"""Validate generated SRD structure without network access."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse


class ValidationError(RuntimeError):
    pass


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: list[str] = []
        self.anchors: set[str] = set()
        self.runtime_assets: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if values.get("data-anchor"):
            self.anchors.add(values["data-anchor"])
        if tag == "script" and values.get("src"):
            self.runtime_assets.append(values["src"])
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.runtime_assets.append(values["href"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])


def _asset_path(public_dir: Path, asset_url: str) -> Path | None:
    parsed = urlparse(asset_url)
    if parsed.scheme or parsed.netloc or asset_url.startswith("//"):
        return None
    path = unquote(parsed.path)
    marker = "/SRD/"
    relative = path.split(marker, 1)[1] if marker in path else path.lstrip("/")
    return public_dir / relative


def validate_site(public_dir: Path) -> None:
    public_dir = Path(public_dir)
    site_path = public_dir / "generated" / "site-index.json"
    search_path = public_dir / "generated" / "search-index.json"
    if not site_path.is_file() or not search_path.is_file():
        raise ValidationError("缺少站点目录或搜索资料")
    site = json.loads(site_path.read_text(encoding="utf-8"))
    search = json.loads(search_path.read_text(encoding="utf-8"))
    anchors_by_page: dict[str, set[str]] = {}
    links_by_page: dict[str, list[str]] = {}

    for page in site.get("pages", []):
        html_path = public_dir / page["path"] / "index.html"
        if not html_path.is_file():
            raise ValidationError(f"页面未生成: {page['path']}")
        parser = PageParser()
        parser.feed(html_path.read_text(encoding="utf-8"))
        duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
        if duplicates:
            raise ValidationError(f"页面存在重复 ID: {page['path']} ({', '.join(duplicates[:5])})")
        anchors_by_page[page["path"]] = parser.anchors | set(parser.ids) | {"top"}
        links_by_page[page["path"]] = parser.links
        for language in ("zh", "en"):
            for heading in page.get("headings", {}).get(language, []):
                if heading["anchor"] not in anchors_by_page[page["path"]]:
                    raise ValidationError(f"目录目标不存在: {page['path']}#{heading['anchor']}")
        for asset in parser.runtime_assets:
            asset_path = _asset_path(public_dir, asset)
            if asset_path is None:
                raise ValidationError(f"运行资源依赖外部地址: {asset}")
            if not asset_path.is_file():
                raise ValidationError(f"运行资源不存在: {asset}")

    for record in search.get("records", []):
        target_anchors = anchors_by_page.get(record["path"])
        if target_anchors is None or record["anchor"] not in target_anchors:
            raise ValidationError(f"搜索目标不存在: {record['path']}#{record['anchor']}")

    def target_anchors(target_path: str) -> set[str] | None:
        if target_path in anchors_by_page:
            return anchors_by_page[target_path]
        html_path = public_dir / target_path / "index.html" if target_path else public_dir / "index.html"
        if not html_path.is_file():
            return None
        parser = PageParser()
        parser.feed(html_path.read_text(encoding="utf-8"))
        anchors_by_page[target_path] = parser.anchors | set(parser.ids) | {"top"}
        return anchors_by_page[target_path]

    for source_path, links in links_by_page.items():
        base_url = f"https://local.invalid/SRD/{source_path.strip('/')}/"
        for href in links:
            parsed = urlparse(href)
            if parsed.scheme or parsed.netloc or href.startswith("//"):
                continue
            resolved = urlparse(urljoin(base_url, href))
            marker = "/SRD/"
            if not resolved.path.startswith(marker):
                continue
            target_path = unquote(resolved.path[len(marker):]).strip("/")
            anchors = target_anchors(target_path)
            if anchors is None:
                file_target = public_dir / target_path
                if not file_target.is_file():
                    raise ValidationError(f"站内链接页面不存在: {source_path} -> {href}")
                if resolved.fragment:
                    raise ValidationError(f"站内文件链接不能定位小节: {source_path} -> {href}")
                continue
            if resolved.fragment and unquote(resolved.fragment) not in anchors:
                raise ValidationError(f"站内链接小节不存在: {source_path} -> {href}")

    for required in ("index.html", "edit/index.html", "admin/index.html", "css/site.css", "js/app.js", "js/search-core.js"):
        if not (public_dir / required).is_file():
            raise ValidationError(f"缺少发布文件: {required}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("public_dir", type=Path)
    args = parser.parse_args()
    validate_site(args.public_dir)
    print("站点结构校验通过")
