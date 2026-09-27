import json
import sys
import subprocess
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_srd


def write_glossary(project, terms):
    result = subprocess.run(['node', str(build_srd.RENDER_CORE_CLI)], input=json.dumps({'mode': 'serialize-glossary', 'terms': terms}), capture_output=True, text=True, encoding='utf-8', check=True)
    (project / 'data/glossary.md').write_text(result.stdout, encoding='utf-8')


def make_project(tmp_path, zh="# 游戏\n\n## 动作掷骰\n\n中文正文", en="# Game\n\n## Action Roll\n\nEnglish body"):
    project = Path(tmp_path)
    (project / "data").mkdir()
    (project / "src" / "pages" / "core").mkdir(parents=True)
    manifest = {
        "version": "test-version",
        "pages": [{"path": "core", "title": {"zh": "核心", "en": "Core"}}],
    }
    (project / "data" / "srd.yaml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    (project / "data" / "glossary.md").write_text("# 规则术语表\n", encoding="utf-8")
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


def test_heading_text_can_change_without_changing_explicit_anchor():
    before = build_srd.assign_anchor_ids("## 动作掷骰 {#action-check}", "## Action Roll {#action-check}")
    after = build_srd.assign_anchor_ids("## 进行动作检定 {#action-check}", "## Make an Action Check {#action-check}")
    assert before == after == (["action-check"], ["action-check"])


def test_duplicate_explicit_anchor_blocks_generation():
    with pytest.raises(build_srd.BuildError, match="重复的显式标题锚点: same"):
        build_srd.assign_anchor_ids(
            "## 一 {#same}\n## 二 {#same}",
            "## One {#same}\n## Two {#same}",
        )


def test_duplicate_heading_anchors_are_unique():
    zh_ids, en_ids = build_srd.assign_anchor_ids("## 一\n## 二", "## Test\n## Test")
    assert zh_ids == ["test", "test-2"]
    assert en_ids == ["test", "test-2"]


def test_rendered_tables_keep_table_layout_inside_width_wrapper():
    markdown = "| 名称 | 阈值 | 护甲值 | 特性 |\n| --- | --- | --- | --- |\n| 皮甲 | 6 / 13 | 3 | 灵活 |"
    rendered = build_srd.render_preview(markdown, "zh")

    assert '<div class="table-scroll" role="region">' in rendered
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


def test_unreferenced_markdown_blocks_generation(tmp_path):
    project = make_project(tmp_path)
    orphan = project / "src" / "pages" / "orphan"
    orphan.mkdir()
    (orphan / "zh.md").write_text("## 遗留正文", encoding="utf-8")
    with pytest.raises(build_srd.BuildError, match=r"(?s)未被 data/srd.yaml 引用.*orphan/zh.md"):
        build_srd.generate_site(project)


def test_placeholder_version_blocks_generation(tmp_path):
    project = make_project(tmp_path)
    manifest_path = project / "data" / "srd.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = "current"
    manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    with pytest.raises(build_srd.BuildError, match="必须使用真实版本号"):
        build_srd.generate_site(project)


def test_empty_glossary_allows_removing_all_hints(tmp_path):
    project = make_project(tmp_path)
    build_srd.generate_site(project)
    assert 'term-link' not in (project / 'content/core/index.md').read_text(encoding='utf-8')


def test_seven_field_terms_allow_manual_explanations_and_blank_links(tmp_path):
    project = make_project(tmp_path, zh="# 游戏\n\n压力点与压力点。", en="# Game\n\nStress and stress.")
    term = {"zh": "压力点", "en": "Stress", "aliases": {"zh": [], "en": []}, "case_sensitive": True, "description": "人工填写的解释。", "url": ""}
    write_glossary(project, [term])
    build_srd.generate_site(project)
    result = (project / "content/core/index.md").read_text(encoding="utf-8")
    assert result.count('class="term-link"') == 1
    assert '<span class="term-link"' in result
    assert 'data-term-quote="人工填写的解释。"' in result
    assert 'data-term-kind' not in result


def test_no_glossary_excludes_nested_text_without_affecting_later_matches():
    terms = [{"zh": "压力点", "aliases": {"zh": []}, "description": "说明", "url": ""}]
    markdown = '## 规则\n\n[[!压力点 **压力点**]]与压力点。'
    rendered = build_srd.render_preview(markdown)
    output = build_srd.apply_glossary_links(rendered, {"terms": terms}, "zh", "/SRD")
    assert output.count('class="term-link"') == 1
    assert '<span class="no-glossary">压力点 <strong>压力点</strong></span>' in output
    assert '</span>与<span class="term-link"' in output
    assert build_srd.apply_glossary_links(rendered, {"terms": terms}, "en", "/SRD") == rendered


def test_no_glossary_block_survives_markdown_rendering():
    terms = [{"zh": "压力点", "aliases": {"zh": []}, "description": "", "url": ""}]
    markdown = '::: no-glossary\n\n压力点\n\n::: no-glossary\n\n压力点\n\n:::\n\n:::\n\n压力点'
    rendered = build_srd.render_preview(markdown)
    output = build_srd.apply_glossary_links(rendered, {"terms": terms}, "zh", "/SRD")
    assert output.count('class="term-link"') == 1
    assert output.count('class="no-glossary"') == 2


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,x", "//example.com", "https:\\evil"])
def test_jump_links_reject_unsafe_protocols(url):
    with pytest.raises(build_srd.BuildError, match="跳转链接无效"):
        build_srd.validate_glossary({"terms": [{"zh": "词", "en": "Term", "url": url}]})


def test_long_terms_are_not_split_into_shorter_terms():
    terms = [
        {"en": "AB", "zh": "甲乙", "aliases": {}, "description": "", "url": ""},
        {"en": "ABCD", "zh": "甲乙丙丁", "aliases": {}, "description": "", "url": ""},
    ]
    for language, text in [("zh", "甲乙丙丁、甲乙、甲乙丙丁")]:
        output = build_srd.apply_glossary_links(f"<p>{text}</p>", {"terms": terms}, language, "/SRD")
        assert output.count('class="term-link"') == 2
        assert output.count('data-term-zh="甲乙丙丁"') == 1
        assert output.count('data-term-zh="甲乙"') == 1
        assert '</span>丙丁' not in output
