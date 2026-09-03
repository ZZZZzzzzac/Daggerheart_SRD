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

    SKIP_TAGS = {"a", "code", "pre", "script", "style", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self, terms: list[dict], language: str, base_path: str):
        super().__init__(convert_charrefs=False)
        self.output: list[str] = []
        self.skip_depth = 0
        self.seen: set[str] = set()
        candidates = []
        for term in terms:
            labels = [term.get(language, ""), *(term.get("aliases", {}).get(language, []) or [])]
            for label in filter(None, labels):
                candidates.append((label, term))
        candidates.sort(key=lambda item: len(item[0]), reverse=True)
        self.candidates = candidates
        self.base_path = "/" + base_path.strip("/") + "/" if base_path.strip("/") else "/"

    def handle_starttag(self, tag, attrs):
        if tag in {"h1", "h2", "h3"}:
            self.seen.clear()
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        self.output.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.output.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.output.append(f"</{tag}>")
        if tag in self.SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)

    def handle_data(self, data):
        if self.skip_depth or not data.strip():
            self.output.append(data)
            return
        output = data
        for label, term in self.candidates:
            term_id = str(term.get("id") or label)
            if term_id in self.seen:
                continue
            flags = re.IGNORECASE if label.isascii() else 0
            escaped = re.escape(label)
            pattern = re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])", flags) if label.isascii() else re.compile(escaped)
            match = pattern.search(output)
            if not match:
                continue
            target = str(term["target"]).strip("/")
            anchor = str(term["anchor"])
            href = f"{self.base_path}{target}/#{anchor}"
            replacement = f'<a class="term-link" href="{html.escape(href, quote=True)}">{match.group(0)}</a>'
            output = output[: match.start()] + replacement + output[match.end() :]
            self.seen.add(term_id)
        self.output.append(output)

    def handle_entityref(self, name):
        self.output.append(f"&{name};")

    def handle_charref(self, name):
        self.output.append(f"&#{name};")

    def handle_comment(self, data):
        self.output.append(f"<!--{data}-->")


def apply_glossary_links(rendered_html: str, glossary: dict, language: str, base_path: str) -> str:
    if not glossary.get("enabled"):
        return rendered_html
    linker = GlossaryLinker(glossary.get("terms", []), language, base_path)
    linker.feed(rendered_html)
    linker.close()
    return "".join(linker.output)


def _plain_text(markdown_text: str) -> str:
    value = re.sub(r"```.*?```", " ", markdown_text, flags=re.DOTALL)
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
    glossary_path = project_dir / "data" / "glossary.yaml"
    pages_dir = project_dir / "src" / "pages"
    content_dir = project_dir / "content"
    generated_dir = project_dir / "static" / "generated"
    if not manifest_path.is_file():
        raise BuildError("缺少唯一章节清单 data/srd.yaml")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    glossary = yaml.safe_load(glossary_path.read_text(encoding="utf-8")) if glossary_path.is_file() else {"enabled": False, "terms": []}
    if glossary.get("enabled") and not glossary.get("terms"):
        raise BuildError("规则术语链接已启用，但术语表为空")

    if content_dir.exists():
        shutil.rmtree(content_dir)
    content_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True, exist_ok=True)
    generate_home(content_dir)

    flat_pages = flatten_pages(manifest)
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
    anchors_by_path: dict[str, dict[str, set[str]]] = {}
    for prepared, rendered in zip(prepared_pages, rendered_pages, strict=True):
        prepared["rendered"] = rendered
        anchors = rendered["anchors"]
        anchors_by_path[prepared["page"]["path"]] = {
            "zh": set(anchors["zh"]),
            "en": set(anchors["en"]),
        }

    if glossary.get("enabled"):
        for term in glossary.get("terms", []):
            if not all(term.get(key) for key in ("id", "target", "anchor")):
                raise BuildError("术语表条目必须包含 id、target 和 anchor")
            target = str(term["target"]).strip("/")
            anchor = str(term["anchor"])
            if target not in anchors_by_path:
                raise BuildError(f"术语 {term['id']} 指向不存在的页面: {target}")
            for language in ("zh", "en"):
                if anchor not in anchors_by_path[target][language]:
                    raise BuildError(f"术语 {term['id']} 指向不存在的 {language} 小节: {target}#{anchor}")

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
        "version": manifest.get("version", "current"),
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
