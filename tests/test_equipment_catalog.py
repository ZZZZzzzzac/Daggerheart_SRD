import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_srd


def test_equipment_children_have_bilingual_item_search_and_legacy_destinations(tmp_path):
    source = 'core-mechanics/equipment'
    shutil.copytree(ROOT / 'src/pages' / source, tmp_path / 'src/pages' / source)
    (tmp_path / 'data').mkdir()
    pages = [{'path': source, 'title': {'zh': '装备', 'en': 'Equipment'}, 'subs': [
        {'path': source + suffix, 'title': {'zh': zh, 'en': en}}
        for suffix, zh, en in [('', '装备规则', 'Equipment Rules'), ('/primary-weapons', '主武器', 'Primary Weapons'), ('/secondary-weapons', '副武器', 'Secondary Weapons'), ('/armor', '护甲', 'Armor'), ('/items', '物品', 'Items'), ('/consumables', '消耗品', 'Consumables')]
    ]}]
    (tmp_path / 'data/srd.yaml').write_text(yaml.safe_dump({'version': 'test', 'pages': pages}, allow_unicode=True), encoding='utf-8')
    (tmp_path / 'data/glossary.md').write_text('# 术语表\n', encoding='utf-8')
    build_srd.generate_site(tmp_path)
    index = json.loads((tmp_path / 'static/generated/search-index.json').read_text(encoding='utf-8'))['records']
    for kind, count in [('primary-weapons', 155), ('secondary-weapons', 37), ('armor', 34), ('items', 60), ('consumables', 60)]:
        rows = [r for r in index if r['path'] == source + '/' + kind]
        zh = {r['anchor']: r for r in rows if r['language'] == 'zh'}
        en = {r['anchor']: r for r in rows if r['language'] == 'en'}
        assert len(zh) == count and zh.keys() == en.keys()
    name = next(r for r in index if r['path'].endswith('/primary-weapons') and r['heading'] == '阔剑')
    assert name['anchor'] == 'gear-tier-1-broadsword'
    parent = (tmp_path / 'content' / source / '_index.md').read_text(encoding='utf-8')
    assert 'data-anchor="magic-weapons" id="magic-weapons" data-equipment-path="core-mechanics/equipment/primary-weapons"' in parent
    assert 'data-anchor="tier-2-levels-24-4" id="tier-2-levels-24-4" data-equipment-path="core-mechanics/equipment/armor"' in parent
    site = json.loads((tmp_path / 'static/generated/site-index.json').read_text(encoding='utf-8'))
    assert site['tree'][0]['type'] == 'group'
    assert len(site['tree'][0]['children']) == 6
