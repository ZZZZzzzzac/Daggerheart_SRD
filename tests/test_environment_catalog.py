import html
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_srd
from adversary_catalog import cards_from_html


def test_environment_cards_preserve_all_source_text_and_anchors():
    folder = ROOT / 'src/pages/adversaries-and-environments/environment-data'
    texts = {lang: (folder / f'{lang}.md').read_text(encoding='utf-8') for lang in ('zh', 'en')}
    plain = {lang: re.sub(r'<!-- /?environment[^\n]*-->', '', text) for lang, text in texts.items()}
    rendered, original = build_srd.render_pairs([texts, plain])
    clean = lambda value: re.sub(r'\s+', '', html.unescape(re.sub(r'<[^>]+>', '', value)))
    for lang in ('zh', 'en'):
        cards = cards_from_html(rendered['html'][lang])
        assert len(cards) == 19
        assert Counter(clean(rendered['html'][lang])) == Counter(clean(original['html'][lang]))
        assert rendered['anchors'][lang] == original['anchors'][lang]
        assert all('environment-brief' in card['html'] for card in cards.values())
    assert cards_from_html(rendered['html']['zh'])['ambushed']['attrs']['data-difficulty'].startswith('特殊')
    assert 'environment-question' in rendered['html']['zh']
    changed = dict(texts)
    changed['zh'] = changed['zh'].replace('**难度：** 10', '**难度：** 18', 1)
    updated = build_srd.render_pairs([changed])[0]
    assert cards_from_html(updated['html']['zh'])['raging-river']['attrs']['data-difficulty'] == '18'
