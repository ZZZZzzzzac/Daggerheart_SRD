import html
from collections import Counter
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import adversary_catalog as catalog
import build_srd


@pytest.fixture(scope="module")
def sources():
    folder = ROOT / "src/pages" / catalog.SOURCE
    return {lang: (folder / f"{lang}.md").read_text(encoding="utf-8") for lang in ("zh", "en")}


def text_only(value):
    return re.sub(r"[\s|]+", "", html.unescape(re.sub(r"<[^>]*>", "", value)))


def test_complete_markdown_content_survives_card_rendering(sources):
    rendered = build_srd.render_pairs([sources])[0]
    unmarked = {lang: re.sub(r"<!-- /?adversary[^\n]*-->", "", text) for lang, text in sources.items()}
    original = build_srd.render_pairs([unmarked])[0]
    for language, expected in (("zh", 139), ("en", 129)):
        cards = catalog.cards_from_html(rendered["html"][language])
        assert len(cards) == expected
        assert Counter(text_only(rendered["html"][language])) == Counter(text_only(original["html"][language]))
        for feature in re.findall(r'<li>[\s\S]*?</li>', original["html"][language]):
            assert text_only(feature) in text_only(rendered["html"][language])
        assert rendered["anchors"][language] == original["anchors"][language]
        assert all('class="stat-values"' in card['html'] for card in cards.values())


def test_editor_and_build_render_updated_fields_from_markdown(sources):
    changed = dict(sources)
    changed['zh'] = changed['zh'].replace('**难度：** 12', '**难度：** 27', 1).replace('锯齿刀盗贼攀爬起来和奔跑一样轻松。', '同步测试：攀爬能力已更新。')
    result = build_srd.render_pairs([changed])[0]
    bandit = catalog.cards_from_html(result['html']['zh'])['jagged-knife-bandit']
    assert bandit['attrs']['data-difficulty'] == '27'
    assert '同步测试：攀爬能力已更新。' in bandit['html']


def test_adversary_headings_do_not_display_anchor_markup(sources):
    rendered = build_srd.render_pairs([sources])[0]
    for language in ('zh', 'en'):
        assert not re.search(r'<h[1-6]\b[^>]*>[^\n]*\{#', rendered['html'][language])


def test_invalid_card_marker_fails_publication(sources):
    changed = dict(sources)
    changed['zh'] = changed['zh'].replace('<!-- /adversary -->', '', 1)
    with pytest.raises(build_srd.BuildError, match='标记不完整'):
        build_srd.render_pairs([changed])


def test_duplicate_card_id_fails_publication(sources):
    changed = dict(sources)
    changed['zh'] = changed['zh'].replace('adversary: zombie-pack |', 'adversary: jagged-knife-bandit |')
    with pytest.raises(build_srd.BuildError, match='ID 重复'):
        build_srd.render_pairs([changed])


def test_editor_can_insert_chinese_card_without_editing_english(sources):
    changed = dict(sources)
    extra = '''<!-- adversary: test-new | Test New -->

#### 新敌人 {#test-new-name}

##### 位阶 1 标准 {#test-new-role}

**难度：** 12 | **阈值：** 8/14 | **生命点：** 5 | **压力点：** 3

<!-- /adversary -->

'''
    changed['zh'] = extra + sources['zh']
    result = build_srd.render_pairs([changed])[0]
    assert len(catalog.cards_from_html(result['html']['zh'])) == 140
    assert len(catalog.cards_from_html(result['html']['en'])) == 129
