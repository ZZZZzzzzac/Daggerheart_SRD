"""Build the bilingual SRD, navigation data, and local search index."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import yaml

from validate_site import ValidationError, validate_site
import adversary_catalog
import domain_catalog


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROJECT_DIR = SCRIPT_DIR.parent
RENDER_CORE_CLI = SCRIPT_DIR / "render_core_cli.mjs"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
EXPLICIT_ID_RE = re.compile(r"\s+\{#([a-zA-Z][\w-]*)\}\s*$")
TAG_RE = re.compile(r"<[^>]+>")


class BuildError(RuntimeError):
    """A user-actionable build validation failure."""


def _clean_heading(value: str) -> str:
    value = EXPLICIT_ID_RE.sub("", value)
    value = TAG_RE.sub("", value)
    value = re.sub(r"[*_`~\[\]]", "", value)
    return html.unescape(value).strip()


def render_pairs(documents: list[dict[str, str]]) -> list[dict]:
    try:
        result = subprocess.run(
            ["node", str(RENDER_CORE_CLI)],
            input=json.dumps({"documents": documents}, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BuildError(f"无法运行 JavaScript 渲染核心: {exc}") from exc
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise BuildError(f"JavaScript 渲染核心失败:\n{details}")
    try:
        rendered = json.loads(result.stdout)["documents"]
    except (KeyError, TypeError, ValueError) as exc:
        raise BuildError("JavaScript 渲染核心返回无效结果") from exc
    if len(rendered) != len(documents):
        raise BuildError("JavaScript 渲染核心返回的页面数量不一致")
    return rendered


def assign_anchor_ids(zh_text: str, en_text: str) -> tuple[list[str], list[str]]:
    anchors = render_pairs([{"zh": zh_text, "en": en_text}])[0]["anchors"]
    return anchors["zh"], anchors["en"]


def render_preview(markdown_text: str, language: str = "zh") -> str:
    rendered = render_pairs([{"zh": markdown_text, "en": markdown_text}])[0]
    return rendered["html"][language]


class GlossaryLinker(HTMLParser):
    """Link the first configured term in each section without touching markup."""

    SKIP_TAGS = {"a", "button", "code", "pre", "script", "style", "textarea", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self, terms: list[dict], language: str, base_path: str):
        super().__init__(convert_charrefs=False)
        self.output: list[str] = []
        self.skip_depth = 0
        self.skip_stack = []
        self.seen: set[str] = set()
        self.language = language
        candidates = []
        for index, term in enumerate(terms):
            label = term.get(language, "")
            if label:
                candidates.append((label, index, term))
        candidates.sort(key=lambda item: (-len(item[0]), item[1]))
        self.matches = {}
        patterns = []
        for label, term_index, term in candidates:
            escaped = re.escape(label)
            matched = escaped
            pattern = rf"(?<![A-Za-z0-9_]){matched}(?![A-Za-z0-9_])" if label.isascii() else escaped
            patterns.append(pattern)
            self.matches.setdefault(label, []).append((label, str(term_index), term))
        self.pattern = re.compile("|".join(patterns)) if patterns else None
        self.base_path = "/" + base_path.strip("/") + "/" if base_path.strip("/") else "/"

    def handle_starttag(self, tag, attrs):
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.seen.clear()
        skip = tag in self.SKIP_TAGS or "no-glossary" in dict(attrs).get("class", "").split()
        if tag not in {"br", "hr", "img", "input", "meta", "link", "wbr", "area", "base", "col", "embed", "param", "source", "track"}:
            self.skip_stack.append((tag, skip))
            self.skip_depth += int(skip)
        self.output.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.output.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.output.append(f"</{tag}>")
        for index in range(len(self.skip_stack) - 1, -1, -1):
            if self.skip_stack[index][0] == tag:
                self.skip_depth -= sum(int(skip) for _, skip in self.skip_stack[index:])
                del self.skip_stack[index:]
                break

    def handle_data(self, data):
        if self.skip_depth or not data.strip() or self.pattern is None:
            self.output.append(data)
            return
        # Match only the original text, never the HTML emitted for an earlier term.
        # A single pass also prevents shorter labels from nesting inside longer ones.
        def replace(match):
            label = match.group(0)
            choices = self.matches.get(label, [])
            chosen = choices[0] if choices else None
            if chosen is None:
                return label
            _, term_id, term = chosen
            if term_id in self.seen:
                return label
            href = term.get("url", "")
            if href and not urlparse(href).scheme and not href.startswith(("/", "#")):
                href = self.base_path + href
            attributes = {
                "data-term-id": term_id,
                "data-term-zh": term.get("zh", ""),
                "data-term-quote": term.get("description", ""),
            }
            if href:
                attributes["href"] = href
            # Blank lines inside an attribute would be parsed as Markdown blocks by Hugo.
            escaped_attributes = {
                key: html.escape(value, quote=True).replace("\n", "&#10;").replace("\r", "&#13;")
                for key, value in attributes.items()
            }
            rendered_attributes = " ".join(f'{key}="{value}"' for key, value in escaped_attributes.items())
            self.seen.add(term_id)
            tag = "a" if href else "span"
            return f'<{tag} class="term-link" {rendered_attributes}>{label}</{tag}>'

        self.output.append(self.pattern.sub(replace, data))

    def handle_entityref(self, name):
        self.output.append(f"&{name};")

    def handle_charref(self, name):
        self.output.append(f"&#{name};")

    def handle_comment(self, data):
        self.output.append(f"<!--{data}-->")


def read_glossary(project_dir: Path) -> dict:
    path = project_dir / "data" / "glossary.md"
    if not path.is_file():
        return {"terms": []}
    result = subprocess.run(
        ["node", str(RENDER_CORE_CLI)],
        input=json.dumps({"mode": "glossary", "markdown": path.read_text(encoding="utf-8")}),
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    if result.returncode:
        raise BuildError(f"术语 Markdown 格式错误：{result.stderr.strip()}")
    return json.loads(result.stdout)


def validate_glossary(glossary: dict) -> None:
    for index, term in enumerate(glossary.get("terms", []), 1):
        if not term.get("zh", "").strip():
            raise BuildError(f"第 {index} 条术语必须填写中文名")
        url = term.get("url", "")
        parsed = urlparse(url)
        if (parsed.scheme and parsed.scheme.lower() not in {"http", "https"}) or url.startswith("//") or any(ord(char) < 32 or char == "\\" for char in url):
            raise BuildError(f"术语 {term['zh']} 的跳转链接无效")


def apply_glossary_links(rendered_html: str, glossary: dict, language: str, base_path: str) -> str:
    if language != "zh":
        return rendered_html
    linker = GlossaryLinker(glossary.get("terms", []), language, base_path)
    linker.feed(rendered_html)
    linker.close()
    return "".join(linker.output)


def _plain_text(markdown_text: str) -> str:
    value = re.sub(r"```.*?```", " ", markdown_text, flags=re.DOTALL)
    value = re.sub(r"^\s*:::(?: no-glossary)?\s*$", "", value, flags=re.MULTILINE)
    value = value.replace("[[!", "").replace("]]", "")
    value = re.sub(r"`[^`]+`", " ", value)
    value = re.sub(r"!\[[^]]*\]\([^)]*\)", " ", value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    value = TAG_RE.sub(" ", value)
    value = re.sub(r"[#>*_~|{}-]+", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def section_records(markdown_text: str, anchor_ids: list[str], page_title: str, path: str, language: str) -> list[dict]:
    matches = list(HEADING_RE.finditer(markdown_text))
    records: list[dict] = []
    if not matches:
        return [{
            "path": path,
            "language": language,
            "pageTitle": page_title,
            "heading": page_title,
            "anchor": "top",
            "body": _plain_text(markdown_text),
        }]
    for index, match in enumerate(matches):
        level = len(match.group(1))
        if level > 3:
            continue
        end = len(markdown_text)
        for next_match in matches[index + 1 :]:
            if len(next_match.group(1)) <= 3:
                end = next_match.start()
                break
        records.append({
            "path": path,
            "language": language,
            "pageTitle": page_title,
            "heading": _clean_heading(match.group(2)),
            "anchor": anchor_ids[index],
            "body": _plain_text(markdown_text[match.end() : end]),
        })
    return records


def read_page(pages_dir: Path, path: str, language: str) -> str:
    file_path = pages_dir / path / f"{language}.md"
    if not file_path.is_file():
        raise BuildError(f"缺少文件: {path}/{language}.md")
    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        raise BuildError(f"内容为空: {path}/{language}.md")
    return content


def flatten_pages(manifest: dict) -> list[dict]:
    pages: list[dict] = []
    for item in manifest.get("pages", []):
        children = item.get("subs")
        if children:
            for child in children:
                page = dict(child)
                page["group"] = item["title"]
                pages.append(page)
        else:
            page = dict(item)
            page["group"] = None
            pages.append(page)
    return pages


def validate_page_inventory(pages_dir: Path, flat_pages: list[dict]) -> None:
    expected = {
        (pages_dir / page["path"] / f"{language}.md").resolve()
        for page in flat_pages
        for language in ("zh", "en")
    }
    actual = {path.resolve() for path in pages_dir.rglob("*.md") if path.is_file()}
    unreferenced = sorted(path.relative_to(pages_dir.resolve()).as_posix() for path in actual - expected)
    if unreferenced:
        details = "\n".join(f"  - {path}" for path in unreferenced)
        raise BuildError(f"发现未被 data/srd.yaml 引用的正文文件:\n{details}")


def _frontmatter(page: dict) -> str:
    return "\n".join([
        "---",
        f"title: {json.dumps(page['title']['zh'], ensure_ascii=False)}",
        f"title_en: {json.dumps(page['title']['en'], ensure_ascii=False)}",
        f"srd_path: {json.dumps(page['path'])}",
        "weight: 1",
        "---",
        "",
    ])


def generate_home(content_dir: Path) -> None:
    home = """---
title: "匕首之心 HTML SRD"
title_en: "Daggerheart HTML SRD"
srd_path: ""
---

<section class="home-hero">
  <p class="eyebrow"><span class="lang-zh">系统参考文档</span><span class="lang-en">System Reference Document</span></p>
  <h1><span class="lang-zh">匕首之心</span><span class="lang-en">Daggerheart</span></h1>
  <p class="home-deck lang-zh">面向跑团现场的双语规则工具。浏览完整章节，搜索正文，或从左侧目录直接抵达需要的规则。</p>
  <p class="home-deck lang-en">A bilingual rules reference built for use at the table. Browse the full structure, search the text, or jump directly to a rule from the contents.</p>
  <p class="home-actions"><a class="primary-link" href="introduction/"><span class="lang-zh">开始阅读</span><span class="lang-en">Start reading</span></a></p>
</section>

<section class="home-note lang-zh">
  <h2>关于本项目</h2>
  <p>《匕首之心》是由 Darrington Press 出版的桌上角色扮演游戏。本站以 HTML 形式整理公开的系统参考文档，并由民间翻译组持续校对。</p>
</section>
<section class="home-note lang-en">
  <h2>About this project</h2>
  <p>Daggerheart is a tabletop roleplaying game published by Darrington Press. This site presents its public System Reference Document in a searchable HTML format.</p>
</section>
"""
    (content_dir / "_index.md").write_text(home, encoding="utf-8")


def generate_site(project_dir: Path) -> tuple[Path, Path]:
    manifest_path = project_dir / "data" / "srd.yaml"
    pages_dir = project_dir / "src" / "pages"
    content_dir = project_dir / "content"
    generated_dir = project_dir / "static" / "generated"
    if not manifest_path.is_file():
        raise BuildError("缺少唯一章节清单 data/srd.yaml")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    version = str(manifest.get("version", "")).strip()
    if not version or version.lower() == "current":
        raise BuildError("data/srd.yaml 必须使用真实版本号，不能留空或使用 current")
    glossary = read_glossary(project_dir)
    validate_glossary(glossary)

    if content_dir.exists():
        shutil.rmtree(content_dir)
    content_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True, exist_ok=True)
    generate_home(content_dir)

    flat_pages = flatten_pages(manifest)
    validate_page_inventory(pages_dir, flat_pages)
    parent_paths = {
        page["path"] for page in flat_pages
        if any(other["path"].startswith(page["path"] + "/") for other in flat_pages)
    }
    prepared_pages: list[dict] = []
    for page in flat_pages:
        path = page["path"]
        zh_text = read_page(pages_dir, path, "zh")
        en_text = read_page(pages_dir, path, "en")
        prepared_pages.append({
            "page": page,
            "zh_text": zh_text,
            "en_text": en_text,
        })
    rendered_pages = render_pairs([
        {
            "zh": prepared["zh_text"],
            "en": prepared["en_text"],
            "pagePath": prepared["page"]["path"],
        }
        for prepared in prepared_pages
    ])
    for prepared, rendered in zip(prepared_pages, rendered_pages, strict=True):
        prepared["rendered"] = rendered

    if (project_dir / "config.yaml").is_file():
        config_documents = yaml.safe_load_all((project_dir / "config.yaml").read_text(encoding="utf-8"))
        config = next((document for document in config_documents if document), {})
    else:
        config = {}
    base_path = urlparse(str((config or {}).get("baseURL", ""))).path
    site_pages: list[dict] = []
    search_records: list[dict] = []
    for position, prepared in enumerate(prepared_pages):
        page = prepared["page"]
        path = page["path"]
        zh_text = prepared["zh_text"]
        en_text = prepared["en_text"]
        rendered = prepared["rendered"]
        zh_anchors = rendered["anchors"]["zh"]
        en_anchors = rendered["anchors"]["en"]
        zh_html = apply_glossary_links(rendered["html"]["zh"], glossary, "zh", base_path)
        en_html = apply_glossary_links(rendered["html"]["en"], glossary, "en", base_path)
        prepared["linked_html"] = {"zh": zh_html, "en": en_html}
        output_dir = content_dir / path
        output_dir.mkdir(parents=True, exist_ok=True)
        page_content = _frontmatter(page) + (
            f'<div class="lang-zh srd-language" lang="zh-CN">\n{zh_html}\n</div>\n'
            f'<div class="lang-en srd-language" lang="en">\n{en_html}\n</div>\n'
        )
        output_name = "_index.md" if path in parent_paths else "index.md"
        (output_dir / output_name).write_text(page_content, encoding="utf-8")

        zh_headings = rendered["headings"]["zh"]
        en_headings = rendered["headings"]["en"]
        site_pages.append({
            "path": path,
            "url": f"{path}/",
            "title": page["title"],
            "group": page.get("group"),
            "previous": flat_pages[position - 1]["path"] if position else None,
            "next": flat_pages[position + 1]["path"] if position + 1 < len(flat_pages) else None,
            "headings": {
                "zh": [
                    {"level": item["level"], "title": item["title"], "anchor": item["anchor"]}
                    for item in zh_headings if item["level"] <= 3
                ],
                "en": [
                    {"level": item["level"], "title": item["title"], "anchor": item["anchor"]}
                    for item in en_headings if item["level"] <= 3
                ],
            },
        })
        search_records.extend(section_records(zh_text, zh_anchors, page["title"]["zh"], path, "zh"))
        search_records.extend(section_records(en_text, en_anchors, page["title"]["en"], path, "en"))

    try:
        domain_catalog.generate(project_dir, prepared_pages, search_records)
        adversary_catalog.generate(project_dir, prepared_pages, site_pages, search_records)
        adversary_catalog.generate(project_dir, prepared_pages, site_pages, search_records, "environment")
    except (ValueError, KeyError) as exc:
        raise BuildError(f"敌人资料库生成失败: {exc}") from exc

    tree: list[dict] = []
    for item in manifest.get("pages", []):
        if item.get("subs"):
            tree.append({
                "type": "group",
                "title": item["title"],
                "children": [child["path"] for child in item["subs"]],
            })
        else:
            tree.append({"type": "page", "path": item["path"]})
    site_index = {
        "version": version,
        "tree": tree,
        "pages": site_pages,
    }
    (generated_dir / "site-index.json").write_text(
        json.dumps(site_index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (generated_dir / "search-index.json").write_text(
        json.dumps({"version": site_index["version"], "records": search_records}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return content_dir, generated_dir


def run_hugo(project_dir: Path, destination: Path) -> None:
    env = os.environ.copy()
    env["PATH"] = str(DEFAULT_PROJECT_DIR) + os.pathsep + env.get("PATH", "")
    command = ["hugo", "--source", str(project_dir), "--destination", str(destination), "--cleanDestinationDir"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise BuildError(f"Hugo 构建失败:\n{details}")
    if not (destination / "index.html").is_file():
        raise BuildError("Hugo 未生成首页")
    try:
        validate_site(destination)
    except ValidationError as exc:
        raise BuildError(f"站点结构校验失败: {exc}") from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    parser.add_argument("--skip-hugo", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_dir = args.project_dir.resolve()
    try:
        manifest = yaml.safe_load((project_dir / "data" / "srd.yaml").read_text(encoding="utf-8"))
        print(f"生成 {len(flatten_pages(manifest))} 个双语页面、整站目录与搜索资料...")
        generate_site(project_dir)
        if not args.skip_hugo:
            print("运行 Hugo...")
            run_hugo(project_dir, project_dir / "public")
        print("构建成功")
        return 0
    except (BuildError, OSError, yaml.YAMLError) as exc:
        print(f"构建失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
