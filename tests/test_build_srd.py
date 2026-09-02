import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_srd


def make_project(tmp_path, zh="# 游戏\n\n## 动作掷骰\n\n中文正文", en="# Game\n\n## Action Roll\n\nEnglish body"):
    project = Path(tmp_path)
    (project / "data").mkdir()
    (project / "src" / "pages" / "core").mkdir(parents=True)
    manifest = {
        "version": "test-version",
        "pages": [{"path": "core", "title": {"zh": "核心", "en": "Core"}}],
    }
    (project / "data" / "srd.yaml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    (project / "data" / "glossary.yaml").write_text("enabled: false\nterms: []\n", encoding="utf-8")
    (project / "src" / "pages" / "core" / "zh.md").write_text(zh, encoding="utf-8")
    (project / "src" / "pages" / "core" / "en.md").write_text(en, encoding="utf-8")
    return project


def test_generate_site_creates_shared_anchor_navigation_and_search(tmp_path):
    project = make_project(tmp_path)
    build_srd.generate_site(project)

    page_html = (project / "content" / "core" / "index.md").read_text(encoding="utf-8")
    assert 'id="action-roll" data-anchor="action-roll"' in page_html
    assert '<h2 data-anchor="action-roll">Action Roll</h2>' in page_html

    site = json.loads((project / "static" / "generated" / "site-index.json").read_text(encoding="utf-8"))
    assert site["version"] == "test-version"
    assert site["pages"][0]["headings"]["zh"][1]["anchor"] == "action-roll"
    assert site["pages"][0]["headings"]["en"][1]["anchor"] == "action-roll"

    search = json.loads((project / "static" / "generated" / "search-index.json").read_text(encoding="utf-8"))
    zh_record = next(item for item in search["records"] if item["language"] == "zh" and item["heading"] == "动作掷骰")
    assert zh_record["anchor"] == "action-roll"
    assert "中文正文" in zh_record["body"]


def test_explicit_anchor_wins_over_generated_slug():
    zh = "## 动作掷骰 {#action-check}"
    en = "## Action Roll {#action-check}"
    zh_ids, en_ids = build_srd.assign_anchor_ids(zh, en)
    assert zh_ids == ["action-check"]
    assert en_ids == ["action-check"]


def test_duplicate_heading_anchors_are_unique():
    zh_ids, en_ids = build_srd.assign_anchor_ids("## 一\n## 二", "## Test\n## Test")
    assert zh_ids == ["test", "test-2"]
    assert en_ids == ["test", "test-2"]


def test_rendered_tables_keep_table_layout_inside_scroll_region():
    markdown = "| 名称 | 阈值 | 护甲值 | 特性 |\n| --- | --- | --- | --- |\n| 皮甲 | 6 / 13 | 3 | 灵活 |"
    rendered = build_srd.render_preview(markdown, "zh")

    assert '<div class="table-scroll" role="region" tabindex="0">' in rendered
    assert "<table>" in rendered
    assert "</table></div>" in rendered


def test_generated_suffix_cannot_collide_with_another_heading_slug():
    zh_ids, _ = build_srd.assign_anchor_ids("## 4\n## 4\n## 4\n## 4 3", "")
    assert zh_ids == ["4", "4-2", "4-3", "4-3-2"]


def test_missing_language_blocks_generation(tmp_path):
    project = make_project(tmp_path)
    (project / "src" / "pages" / "core" / "en.md").unlink()
    with pytest.raises(build_srd.BuildError, match="缺少文件"):
        build_srd.generate_site(project)


def test_enabled_empty_glossary_blocks_generation(tmp_path):
    project = make_project(tmp_path)
    (project / "data" / "glossary.yaml").write_text("enabled: true\nterms: []\n", encoding="utf-8")
    with pytest.raises(build_srd.BuildError, match="术语表为空"):
        build_srd.generate_site(project)


def test_glossary_links_first_term_per_section_and_skips_existing_markup(tmp_path):
    project = make_project(
        tmp_path,
        zh="# 游戏\n\n## 动作掷骰\n\n优势与优势。\n\n## 其他\n\n`优势`、[优势](https://example.com)与优势。",
        en="# Game\n\n## Action Roll\n\nAdvantage and Advantage.\n\n## Other\n\n`Advantage`, [Advantage](https://example.com), and Advantage.",
    )
    glossary = {
        "enabled": True,
        "terms": [{
            "id": "advantage", "zh": "优势", "en": "Advantage",
            "target": "core", "anchor": "action-roll", "aliases": {"zh": [], "en": []},
        }],
    }
    (project / "data" / "glossary.yaml").write_text(yaml.safe_dump(glossary, allow_unicode=True), encoding="utf-8")
    build_srd.generate_site(project)
    generated = (project / "content" / "core" / "index.md").read_text(encoding="utf-8")
    assert generated.count('class="term-link"') == 4
    assert '<code>优势</code>' in generated
    assert '<a href="https://example.com">优势</a>' in generated
