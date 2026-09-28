import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { renderPair } from '../static/js/render-core.mjs';
import { compareEquipment } from '../static/js/equipment-core.mjs';

for (const [kind,count] of [['primary-weapons',155],['secondary-weapons',37],['armor',34]]) {
  test(`${kind} 保留所有双语装备、原小节锚点和格式，空表行不算装备`, () => {
    const path = `core-mechanics/equipment/${kind}`;
    const source = ['zh','en'].map(lang => readFileSync(new URL(`../src/pages/${path}/${lang}.md`,import.meta.url),'utf8'));
    const result = renderPair(...source,{pagePath:path});
    const ids = {};
    for (const lang of ['zh','en']) {
      ids[lang] = [...result.html[lang].matchAll(/<tr data-anchor="([^"]+)"/g)].map(m => m[1]);
      assert.equal(ids[lang].length,count);
      assert.equal(new Set(ids[lang]).size,count);
      for (const anchor of result.anchors[lang]) assert.ok(result.html[lang].includes(`data-anchor="${anchor}"`),anchor);
      assert.equal((result.html[lang].match(/<table /g)||[]).length,1);
    }
    assert.deepEqual(ids.zh,ids.en);
    if (kind !== 'armor') {
      assert.match(result.html.zh, /data-column="type"[^>]*>物理<\/td>/);
      assert.match(result.html.en, /data-column="type"[^>]*>Physical<\/td>/);
      for (const match of result.html.en.matchAll(/<td data-column="damage"[^>]*>([\s\S]*?)<\/td>/g)) assert.doesNotMatch(match[1],/\b(?:phy|mag)\b/);
      if (kind === 'primary-weapons') assert.match(result.html.en, /data-column="type"[^>]*>Physical \/ Magic<\/td>/);
    }
    if (kind==='primary-weapons') {
      assert.match(result.html.zh, /data-search="阔剑broadsword"/);
      assert.match(result.html.zh, /<strong>迅捷：<\/strong>/);
      const broken = source[1].replace(/\| Broadsword[^\n]*\n/, '');
      assert.throws(() => renderPair(source[0],broken,{pagePath:path}),/中英文装备表条目/);
    }
    if (kind==='armor') {
      const edited = source[0].replace(/(\| \*\*填充布甲\*\* \| 5 \/ 11 \|\s*)3/, '$19');
      assert.notEqual(edited, source[0]);
      const preview = renderPair(edited, source[1], {pagePath:path});
      assert.match(preview.html.zh, /data-column="armor" data-value="9"/);
      assert.match(preview.html.en, /data-column="armor" data-value="3"/);
    }
  });
}

test('排序按实际数字、骰面与射程远近，而非字符串顺序', () => {
  assert.ok(compareEquipment('d8+10 phy','d10+2 phy','damage')<0);
  assert.ok(compareEquipment('d10+2','d10+11','damage')<0);
  assert.ok(compareEquipment('9 / 23','11 / 24','thresholds')<0);
  assert.ok(compareEquipment('11 / 23','11 / 24','thresholds')<0);
  assert.ok(compareEquipment('Very Close','Close','range')<0);
  assert.ok(compareEquipment('Far','Very Far','range')<0);
  assert.ok(compareEquipment('3','8','armor')<0);
});

for (const kind of ['items','consumables']) {
  test(`${kind} 按掷骰编号关联全部 60 条，所有表头均为查询`,()=>{
    const path=`core-mechanics/equipment/${kind}`;
    const sources=['zh','en'].map(lang=>readFileSync(new URL(`../src/pages/${path}/${lang}.md`,import.meta.url),'utf8'));
    const result=renderPair(...sources,{pagePath:path});
    for(const lang of ['zh','en']) {
      const ids=[...result.html[lang].matchAll(/<tr data-anchor="([^"]+)"/g)].map(m=>m[1]);
      assert.deepEqual(ids,Array.from({length:60},(_,i)=>`${kind}-${String(i+1).padStart(2,'0')}`));
      assert.doesNotMatch(result.html[lang],/data-filter="choices"/);
      assert.equal((result.html[lang].match(/data-filter="text"/g)||[]).length,3);
    }
    if(kind==='items') assert.match(result.html.zh,/id="items-22"[^>]*>[\s\S]*?壁虎手套/);
  });
}
