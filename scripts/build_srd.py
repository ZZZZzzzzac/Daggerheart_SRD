"""Build the bilingual SRD, navigation data, and local search index."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import yaml

from validate_site import ValidationError, validate_site
import adversary_catalog
import domain_catalog
import equipment_catalog
import page_redirects


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROJECT_DIR = SCRIPT_DIR.parent
RENDER_CORE_CLI = SCRIPT_DIR / "render_core_cli.mjs"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
EXPLICIT_ID_RE = re.compile(r"\s+\{#([a-zA-Z][\w-]*)\}\s*$")
TAG_RE = re.compile(r"<[^>]+>")
EXPORT_ZIP_NAME = "daggerheart-srd-md.zip"
EXPORT_ARCHIVE_ROOT = "Daggerheart-SRD-MD"
# 导出文件里写的授权声明与站点地址；config.yaml 缺少 baseURL 时用这个地址。
EXPORT_LICENSE = (
    "© 2025 Critical Role LLC. 依据 Darrington Press 社群游戏授权条款"
    "（https://www.darringtonpress.com/license）发布，视为 Public Game Content。"
)
EXPORT_SITE_URL = "https://daggerheart.cn/SRD/"
ANCHOR_SPAN_LINE_RE = re.compile(r'^[ \t]*<span\b[^>]*data-anchor="[^"]*"[^>]*>[ \t]*</span>[ \t]*$', re.MULTILINE)
CARD_MARKER_LINE_RE = re.compile(r'^[ \t]*<!--[ \t]*/?[ \t]*(?:adversary|environment)\b[^>]*-->[ \t]*$', re.MULTILINE)
INLINE_NO_GLOSSARY_RE = re.compile(r'\[\[!(.*?)\]\]', re.DOTALL)
IMAGE_TAG_RE = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
PARAGRAPH_LINE_RE = re.compile(r'^[ \t]*<p\b[^>]*>(.*?)</p>[ \t]*$', re.MULTILINE)


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
        # 中英文的标题层级不一定一致；每个显式小节都可作为双语关联目标。
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
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


FENCE_PREFIXES = ("```", "~~~")


def _scanned_lines(lines: list[str]) -> Iterator[tuple[int, str, bool]]:
    """Yield (index, line, in_fence); 代码围栏里的行不参与标题与链接改写。"""
    in_fence = False
    for index, line in enumerate(lines):
        if line.lstrip().startswith(FENCE_PREFIXES):
            in_fence = not in_fence
            yield index, line, True
            continue
        yield index, line, in_fence


def _strip_no_glossary_fences(lines: list[str]) -> None:
    """`::: no-glossary` 只给本站渲染器看，导出时连同配对的 `:::` 一起去掉。"""
    depth = 0
    for index, line, in_fence in _scanned_lines(lines):
        if in_fence:
            continue
        stripped = line.strip()
        if stripped == "::: no-glossary":
            depth += 1
            lines[index] = ""
        elif stripped == ":::" and depth:
            depth -= 1
            lines[index] = ""


def clean_export_markdown(markdown_text: str) -> str:
    """Strip site-only markup so the exported file is plain Markdown."""
    value = INLINE_NO_GLOSSARY_RE.sub(r"\1", markdown_text)
    value = ANCHOR_SPAN_LINE_RE.sub("", value)
    value = CARD_MARKER_LINE_RE.sub("", value)
    value = PARAGRAPH_LINE_RE.sub(r"\1", value)
    value = IMAGE_TAG_RE.sub("", value)
    # 显式锚点只有本站渲染器认得，导出时去掉，标题只留文字。
    value = re.sub(r"^(#{1,6}[ \t]+.*?)[ \t]*\{#[a-zA-Z][\w-]*\}", r"\1", value, flags=re.MULTILINE)
    lines = value.split("\n")
    _strip_no_glossary_fences(lines)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _export_headings(lines: list[str]) -> list[tuple[int, int, str]]:
    headings: list[tuple[int, int, str]] = []
    for index, line, in_fence in _scanned_lines(lines):
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), _clean_heading(match.group(2))))
    return headings


def normalize_export_headings(markdown_text: str, page_title: str) -> str:
    """Drop a repeated page title and level the remaining sections continuously."""
    lines = markdown_text.split("\n")
    headings = _export_headings(lines)
    if headings and headings[0][2].casefold() == page_title.strip().casefold():
        del lines[headings[0][0]]
        headings = _export_headings(lines)
    if not headings:
        return "\n".join(lines)
    # 源稿混用了 # 与 ##/###/####：按出现过的层级排序后连续映射到 2、3、4…，
    # 既保留原有从属关系，也不会把同级小节拆成父子。
    mapping = {
        level: min(2 + rank, 6)
        for rank, level in enumerate(sorted({level for _, level, _ in headings}))
    }
    for index, line, in_fence in _scanned_lines(lines):
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            lines[index] = "#" * mapping[len(match.group(1))] + " " + match.group(2)
    return "\n".join(lines)


def page_markdown(page_title: str, markdown_text: str) -> str:
    """Render one chapter: the page title becomes the only level-1 heading."""
    body = normalize_export_headings(clean_export_markdown(markdown_text), page_title)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return f"# {page_title}\n\n{body}\n" if body else f"# {page_title}\n"


def absolutize_export_links(markdown_text: str, site_url: str) -> str:
    """Rewrite site-absolute links so they still work outside the site."""
    base = site_url.rstrip("/")
    prefix = urlparse(site_url).path.rstrip("/")
    if not prefix:
        # 站点部署在根路径时无法区分站内链接，保持原样。
        return markdown_text
    lines = markdown_text.split("\n")
    for index, line, in_fence in _scanned_lines(lines):
        if in_fence or "](" not in line:
            continue
        lines[index] = line.replace(f"]({prefix}/", f"]({base}/").replace(f"]({prefix})", f"]({base}/)")
    return "\n".join(lines)


def _export_complete_markdown(language: str, version: str, site_url: str, body: str) -> str:
    if language == "zh":
        title = "匕首之心系统参考文档"
        meta = f"版本 {version} ｜ 来源 {site_url}"
        note = "本文件把站内全部章节按目录顺序合并为一份 Markdown 文档；每章也可在 chapters/ 目录单独取用。"
    else:
        title = "Daggerheart System Reference Document"
        meta = f"Version {version} | Source {site_url}"
        note = "This file merges every chapter of the site into one Markdown document in contents order; each chapter is also available separately in the chapters/ directory."
    return f"# {title}\n\n{meta}\n\n{note}\n\n{EXPORT_LICENSE}\n\n{body}\n"


def _export_readme(version: str, site_url: str, chapters: dict[str, list[tuple[str, str, str]]]) -> str:
    lines = [
        "# 匕首之心 SRD · Markdown 导出",
        "",
        f"- 版本：{version}",
        f"- 来源：{site_url}",
        f"- 授权：{EXPORT_LICENSE}",
        "",
        "## 内容结构",
        "",
        "```",
        f"{EXPORT_ARCHIVE_ROOT}/",
        "├── README.md",
        "├── zh/",
        "│   ├── complete.md          # 全部中文章节合并版",
        "│   └── chapters/            # 按站内目录顺序的章节文件",
        "└── en/",
        "    ├── complete.md          # 全部英文章节合并版",
        "    └── chapters/",
        "```",
        "",
        "说明：",
        "",
        "- 章节文件名前的数字是站内目录顺序，中英文编号一一对应。",
        "- 每章以页面标题作为一级标题，章内小节依次顺延，最浅的小节为二级标题。",
        "- 站点专用的锚点标记、术语链接和敌人数据注释已移除，正文为纯 Markdown；表格、列表和强调保持原样。",
        "",
        "## English",
        "",
        "This archive contains the whole bilingual SRD as Markdown. `zh/complete.md` and `en/complete.md` hold every chapter, while `zh/chapters/` and `en/chapters/` hold the same chapters separately in site contents order.",
        "",
        "## 章节顺序 Chapters",
        "",
        "### 中文",
        "",
    ]
    lines.extend(f"- `{filename}` {title}" for filename, title, _ in chapters["zh"])
    lines.extend(["", "### English", ""])
    lines.extend(f"- `{filename}` {title}" for filename, title, _ in chapters["en"])
    lines.append("")
    return "\n".join(lines)


def _write_zip_entry(archive: zipfile.ZipFile, name: str, text: str) -> None:
    # 固定时间戳，相同内容每次构建出的压缩包字节一致。
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3  # 固定宿主标识，Windows 与 Linux 构建字节一致
    info.external_attr = 0o644 << 16
    archive.writestr(info, text)


def generate_markdown_export(
    generated_dir: Path, version: str, site_url: str, prepared_pages: list[dict]
) -> Path:
    """Package the whole site as Markdown for the reader download button."""
    chapters: dict[str, list[tuple[str, str, str]]] = {"zh": [], "en": []}
    for language in ("zh", "en"):
        for index, prepared in enumerate(prepared_pages, 1):
            page = prepared["page"]
            title = page["title"][language]
            filename = f"{index:02d}-{page['path'].replace('/', '-')}.md"
            chapters[language].append(
                (
                    filename,
                    title,
                    absolutize_export_links(
                        page_markdown(title, prepared[f"{language}_text"]), site_url
                    ),
                )
            )
    target = generated_dir / "export" / EXPORT_ZIP_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        _write_zip_entry(archive, f"{EXPORT_ARCHIVE_ROOT}/README.md", _export_readme(version, site_url, chapters))
        for language, entries in chapters.items():
            body = "\n\n".join(text for _, _, text in entries)
            _write_zip_entry(
                archive,
                f"{EXPORT_ARCHIVE_ROOT}/{language}/complete.md",
                _export_complete_markdown(language, version, site_url, body),
            )
            for filename, _, text in entries:
                _write_zip_entry(archive, f"{EXPORT_ARCHIVE_ROOT}/{language}/chapters/{filename}", text)
    # 先写临时文件再替换，避免中断后留下截断的压缩包。
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_bytes(buffer.getvalue())
    os.replace(temporary, target)
    return target


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
    site_url = str((config or {}).get("baseURL", "")).strip() or EXPORT_SITE_URL
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
        page_redirects.generate(project_dir, prepared_pages)
        equipment_catalog.generate(project_dir, prepared_pages, search_records)
        domain_catalog.generate(project_dir, prepared_pages, search_records)
        adversary_catalog.generate(project_dir, prepared_pages, site_pages, search_records)
        adversary_catalog.generate(project_dir, prepared_pages, site_pages, search_records, "environment")
    except (ValueError, KeyError) as exc:
        raise BuildError(f"资料库生成失败: {exc}") from exc

    # 轮椅规则已并入装备，旧页面仅用于跳转，不进入目录和搜索索引。
    if any(page["path"] == "core-mechanics/equipment" for page in site_pages):
        redirect_dir = content_dir / "core-mechanics" / "combat-wheelchair"
        redirect_dir.mkdir(parents=True, exist_ok=True)
        (redirect_dir / "index.md").write_text(
            '---\ntitle: "战斗轮椅"\nlayout: "wheelchair-redirect"\n---\n', encoding="utf-8"
        )

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
    # 整站 Markdown 打包放在静态资源里，由阅读端“导出 MD”按钮直接下载。
    generate_markdown_export(generated_dir, version, site_url, prepared_pages)
    return content_dir, generated_dir


def prepare_browser_modules(destination: Path) -> None:
    """发布标准 .js 模块地址，兼容未配置 .mjs MIME 类型的静态服务器。"""
    for source in list(destination.rglob('*.mjs')):
        alias = source.with_suffix('.js')
        if alias.exists():
            raise BuildError(f'浏览器模块路径冲突: {alias.relative_to(destination)}')
        alias.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
    # 仅处理脚本字符串和 HTML 资源属性，不替换规则正文中的普通文字。
    for script in destination.rglob('*.js'):
        text = script.read_text(encoding='utf-8')
        updated = re.sub(r'''\.mjs(?=[?'"`])''', '.js', text)
        if updated != text:
            script.write_text(updated, encoding='utf-8')
    for page in destination.rglob('*.html'):
        text = page.read_text(encoding='utf-8')
        updated = re.sub(r'''(\b(?:src|href)=["'][^"']*)\.mjs(?=[?"'])''', r'\1.js', text)
        if updated != text:
            page.write_text(updated, encoding='utf-8')


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
    prepare_browser_modules(destination)
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
