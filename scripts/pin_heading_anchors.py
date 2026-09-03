"""Persist the current generated heading anchors in bilingual SRD Markdown."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

import build_srd


HEADING_LINE_RE = re.compile(r"^(#{1,6}[ \t]+.+?)([ \t]*)$", re.MULTILINE)


def pin_anchors(markdown: str, anchors: list[str]) -> str:
    index = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal index
        heading = match.group(1)
        if build_srd.EXPLICIT_ID_RE.search(heading):
            index += 1
            return heading.rstrip()
        anchor = anchors[index]
        index += 1
        return f"{heading.rstrip()} {{#{anchor}}}"

    result = HEADING_LINE_RE.sub(replace, markdown)
    if index != len(anchors):
        raise build_srd.BuildError(f"标题数量与锚点数量不一致: {index} / {len(anchors)}")
    return result


def main() -> int:
    project_dir = Path(__file__).resolve().parent.parent
    manifest = yaml.safe_load((project_dir / "data" / "srd.yaml").read_text(encoding="utf-8")) or {}
    for page in build_srd.flatten_pages(manifest):
        page_dir = project_dir / "src" / "pages" / page["path"]
        zh_path = page_dir / "zh.md"
        en_path = page_dir / "en.md"
        zh_text = zh_path.read_text(encoding="utf-8")
        en_text = en_path.read_text(encoding="utf-8")
        zh_anchors, en_anchors = build_srd.assign_anchor_ids(zh_text, en_text)
        zh_path.write_text(pin_anchors(zh_text, zh_anchors), encoding="utf-8")
        en_path.write_text(pin_anchors(en_text, en_anchors), encoding="utf-8")
        print(f"已固定 {page['path']} 的 {len(zh_anchors)} / {len(en_anchors)} 个中英文锚点")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
