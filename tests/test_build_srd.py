import json
import sys
import subprocess
import hashlib
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_srd


def write_glossary(project, terms):
    for term in terms:
        term.setdefault('enabled', True)
        term.setdefault('aliases', {'zh': [], 'en': []})
        term.setdefault('definition', {language: {'mode': 'quote', 'reviewer': '', 'reviewedAt': '', 'hash': ''} for language in ('zh', 'en')})
        if isinstance(term['anchor'], str):
            term['anchor'] = {'zh': term['anchor'], 'en': term['anchor']}
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
            "quote": {"zh": "优势与优势。", "en": "Advantage and Advantage."},
        }],
    }
    write_glossary(project, glossary["terms"])
    build_srd.generate_site(project)
    generated = (project / "content" / "core" / "index.md").read_text(encoding="utf-8")
    assert generated.count('class="term-link"') == 4
    assert '<code>优势</code>' in generated
    assert '<a href="https://example.com">优势</a>' in generated


def test_glossary_matches_original_text_only_and_prefers_long_terms():
    terms = [
        {"id": "armor", "zh": "护甲", "en": "Armor", "target": "armor", "anchor": "armor"},
        {"id": "slots", "zh": "护甲槽", "en": "Armor Slot", "target": "armor", "anchor": "slots", "quote": {"en": 'Armor <script> & "quoted"'}},
        {"id": "advantage", "zh": "优势", "en": "Advantage", "target": "rules", "anchor": "advantage"},
    ]
    source = '<h4>Armor Slot</h4><p title="Armor">Armor Slot, Armor Slot, Armor, disadvantage, ADVANTAGE, Advantage.</p><a href="/armor/">Armor</a><code>Armor</code><button>Armor</button><h4>Next</h4><p>Armor</p>'
    output = build_srd.apply_glossary_links(source, {"enabled": True, "terms": terms}, "en", "/SRD/")
    assert output.count('class="term-link"') == 4
    assert '>Armor Slot</a>, Armor Slot, <a' in output
    assert ', disadvantage, <a' in output
    assert '>ADVANTAGE</a>, Advantage.' in output
    assert 'title="Armor"' in output
    assert '<a href="/armor/">Armor</a><code>Armor</code><button>Armor</button>' in output
    assert 'href="/SRD/armor/#slots"' in output
    assert 'data-term-quote="Armor &lt;script&gt; &amp; &quot;quoted&quot;"' in output
    assert '<h4>Armor Slot</h4>' in output

    class LinkDepth(build_srd.HTMLParser):
        depth = 0
        maximum = 0

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self.depth += 1
                self.maximum = max(self.maximum, self.depth)

        def handle_endtag(self, tag):
            if tag == "a":
                self.depth -= 1

    parser = LinkDepth()
    parser.feed(output)
    assert parser.maximum == 1
    assert parser.depth == 0


def test_glossary_uses_each_languages_actual_target(tmp_path):
    project = make_project(tmp_path, zh="## 压力点 {#legacy-stress}\n\n压力点。", en="## Stress {#legacy-stress}\n\nStress.\n\n## More Stress {#stress-rule}\n\nMental strain.")
    term = {"id": "stress", "zh": "压力点", "en": "Stress", "target": "core", "anchor": {"zh": "legacy-stress", "en": "stress-rule"}, "quote": {"zh": "压力点。", "en": "Mental strain."}}
    write_glossary(project, [term])
    build_srd.generate_site(project)
    output = (project / "content" / "core" / "index.md").read_text(encoding="utf-8")
    assert 'href="/core/#legacy-stress"' in output
    assert 'href="/core/#stress-rule"' in output
    assert 'data-term-quote="压力点。"' in output
    assert 'data-term-quote="Mental strain."' in output


@pytest.mark.parametrize("change, error", [
    ({"quote": {"zh": "说明"}}, "缺少 en 原文摘录"),
    ({"anchor": {"zh": "rule", "en": "missing"}}, "不存在的 en 小节"),
    ({"id": "not valid"}, "ID 无效"),
    ({"aliases": {"en": ["STRESS"]}}, "名称或别名重复"),
    ({"aliases": {"en": "Stress"}}, "别名必须"),
    ({"target": "missing"}, "不存在的页面"),
])
def test_glossary_invalid_definitions_fail_build(change, error):
    term = {"id": "stress", "zh": "压力点", "en": "Stress", "target": "core", "anchor": "rule", "quote": {"zh": "说明", "en": "Summary"}}
    term.update(change)
    with pytest.raises(build_srd.BuildError, match=error):
        build_srd.validate_glossary({"terms": [term]}, {"core": {"zh": {"rule"}, "en": {"rule"}}}, {"core": {"zh": {"rule": ["说明"]}, "en": {"rule": ["Summary"]}}})


def test_glossary_rejects_duplicate_ids():
    term = {"id": "stress", "zh": "压力点", "en": "Stress", "target": "core", "anchor": "rule", "quote": {"zh": "说明", "en": "Summary"}}
    with pytest.raises(build_srd.BuildError, match="ID 无效或重复"):
        build_srd.validate_glossary({"terms": [term, term]}, {"core": {"zh": {"rule"}, "en": {"rule"}}}, {"core": {"zh": {"rule": ["说明"]}, "en": {"rule": ["Summary"]}}})


def test_glossary_rejects_paraphrases_wrong_sections_and_stale_quotes():
    term = {"id": "stress", "zh": "压力点", "en": "Stress", "target": "core", "anchor": "rule", "quote": {"zh": "原文。", "en": "Original."}}
    anchors = {"core": {"zh": {"rule", "other"}, "en": {"rule"}}}
    blocks = {"core": {"zh": {"rule": ["原文。"], "other": ["别处原文。"]}, "en": {"rule": ["Original."]}}}
    build_srd.validate_glossary({"terms": [term]}, anchors, blocks)
    for text in ("改写原文。", "别处原文。", "旧版原文。", "原文"):
        term["quote"]["zh"] = text
        with pytest.raises(build_srd.BuildError, match="禁止自行概括"):
            build_srd.validate_glossary({"terms": [term]}, anchors, blocks)
    term["summary"] = {"zh": "未经审核", "en": "Unreviewed"}
    with pytest.raises(build_srd.BuildError, match="不允许未经审核"):
        build_srd.validate_glossary({"terms": [term]}, anchors, blocks)


def test_source_quotes_preserve_complete_contiguous_blocks_and_only_remove_formatting():
    blocks = build_srd.source_blocks('<h2 data-anchor="rule">规则</h2><p>原文<strong>强调</strong> &amp; 内容。</p><ul><li>第一项。</li><li>第二项。</li></ul><h3 data-anchor="other">其他</h3><p>其他内容。</p>')
    assert blocks == {"rule": ["原文强调 & 内容。", "第一项。", "第二项。"], "other": ["其他内容。"]}
    term = {"id": "test", "zh": "术语", "en": "Term", "target": "core", "anchor": "rule", "quote": {"zh": "原文强调 & 内容。\n\n第一项。", "en": "Original."}}
    anchors = {"core": {"zh": {"rule"}, "en": {"rule"}}}
    sources = {"core": {"zh": blocks, "en": {"rule": ["Original."]}}}
    build_srd.validate_glossary({"terms": [term]}, anchors, sources)
    term["quote"]["zh"] = "原文强调 & 内容。\n\n第二项。"
    with pytest.raises(build_srd.BuildError, match="禁止自行概括"):
        build_srd.validate_glossary({"terms": [term]}, anchors, sources)


def test_markdown_is_the_only_glossary_source():
    project = Path(__file__).resolve().parents[1]
    glossary = build_srd.read_glossary(project)
    assert len(glossary['terms']) == 328
    assert sum(term['enabled'] for term in glossary['terms']) == 14
    term = next(term for term in glossary['terms'] if term['id'] == 'armor-slots')
    assert term['zh'] == '护甲槽'
    assert term['en'] == 'Armor Slot'
    assert term['aliases']['en'] == ['Armor Slots']
    assert term['case_sensitive'] is True
    output = build_srd.apply_glossary_links('<p>armor slot; Armor Slots; Armor Slot.</p>', {'enabled': True, 'terms': [term]}, 'en', '/SRD')
    assert '<p>armor slot; <a' in output
    assert output.count('class="term-link"') == 1


def test_multiline_quotes_do_not_break_hugo_raw_html_attributes():
    term = {"id": "test", "zh": "术语", "en": "Term", "target": "core", "anchor": "rule", "quote": {"zh": "第一段。\n\n第二段。"}}
    output = build_srd.apply_glossary_links('<p>术语</p><h2 id="rule">规则</h2>', {"enabled": True, "terms": [term]}, "zh", "/SRD")
    assert 'data-term-quote="第一段。&#10;&#10;第二段。"' in output
    assert '\n' not in output


def test_manual_explanation_requires_current_review_record():
    term = {"id": "stress", "zh": "压力点", "en": "Stress", "target": "core", "anchor": "rule", "quote": {"zh": "测试用的人工文案。", "en": "Original."}, "definition": {"zh": {"mode": "pending"}, "en": {"mode": "quote"}}}
    anchors = {"core": {"zh": {"rule"}, "en": {"rule"}}}
    blocks = {"core": {"zh": {"rule": ["原文。"]}, "en": {"rule": ["Original."]}}}
    with pytest.raises(build_srd.BuildError, match="尚未审核"):
        build_srd.validate_glossary({"terms": [term]}, anchors, blocks)
    payload = "\n".join([term["id"], term["zh"], term["en"], term["target"], "rule", term["quote"]["zh"]])
    term["definition"]["zh"] = {"mode": "approved", "reviewer": "测试审核人", "reviewedAt": "2026-09-26", "hash": hashlib.sha256(payload.encode()).hexdigest()}
    build_srd.validate_glossary({"terms": [term]}, anchors, blocks)
    term["quote"]["zh"] += "修改"
    with pytest.raises(build_srd.BuildError, match="审核记录缺失或文案已变化"):
        build_srd.validate_glossary({"terms": [term]}, anchors, blocks)
