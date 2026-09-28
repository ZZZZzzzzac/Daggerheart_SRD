const test = require("node:test");
const assert = require("node:assert/strict");
const search = require("../static/js/search-core.js");

const records = [
  { language: "zh", pageTitle: "动作掷骰", heading: "概览", body: "普通正文", path: "page", anchor: "a" },
  { language: "zh", pageTitle: "核心机制", heading: "动作掷骰", body: "普通正文", path: "page", anchor: "b" },
  { language: "zh", pageTitle: "核心机制", heading: "其他", body: "这里解释动作掷骰", path: "page", anchor: "c" },
  { language: "en", pageTitle: "Action Roll", heading: "Overview", body: "English", path: "page", anchor: "d" },
];

test("page title ranks above section title and body", () => {
  const results = search.search(records, "动作掷骰", "zh");
  assert.deepEqual(results.map((item) => item.record.anchor), ["a", "b", "c"]);
});

test("没有对应小节的原文命中只定位目标语言章节", () => {
  const result = search.search(records, "Action Roll", "zh")[0];
  assert.equal(result.record.language, "zh");
  assert.equal(result.record.anchor, "top");
  assert.equal(result.chapterOnly, true);
  assert.equal(result.sourceRecord.language, "en");
  assert.equal(search.search(records, "Action Roll", "en")[0].record.anchor, "d");
});

test("search does not guess misspellings", () => {
  assert.equal(search.search(records, "动做掷骰", "zh").length, 0);
});

const bilingual = [
  { language: 'zh', path: 'core', anchor: 'stress', pageTitle: '核心机制', heading: '压力点', body: '承受压力。' },
  { language: 'en', path: 'core', anchor: 'stress', pageTitle: 'Core', heading: 'Stress', body: 'Mark stress when exhausted.' },
  { language: 'zh', path: 'core', anchor: 'rest', pageTitle: '核心机制', heading: '休整', body: '清除压力点。' },
  { language: 'en', path: 'core', anchor: 'rest', pageTitle: 'Core', heading: 'Rest', body: 'Clear stress.' },
];

test('英文标题或正文命中显示同锚点中文，中文查询也能反向关联', () => {
  for (const query of ['Stress', 'exhausted']) {
    const result = search.search(bilingual, query, 'zh')[0];
    assert.equal(result.record.heading, '压力点');
    assert.equal(result.record.body, '承受压力。');
    assert.equal(result.sourceRecord.language, 'en');
    assert.equal(result.chapterOnly, false);
  }
  const result = search.search(bilingual, '压力点', 'en')[0];
  assert.equal(result.record.heading, 'Stress');
  assert.equal(result.sourceRecord.language, 'zh');
});

test('同一小节的双语命中去重后再限量，同分优先显示语言的命中', () => {
  const both = bilingual.map(r => ({ ...r, body: 'shared' }));
  const results = search.search(both, 'shared', 'zh', 2);
  assert.equal(results.length, 2);
  assert.deepEqual(results.map(r => r.record.anchor), ['stress', 'rest']);
  assert.ok(results.every(r => r.sourceRecord.language === 'zh'));
});

test('名称相同或锚点相同但页面不同的结果不会被合并', () => {
  const copies = bilingual.map(r => ({ ...r, path: 'other' }));
  const results = search.search([...bilingual, ...copies], 'Stress', 'zh');
  assert.equal(results.length, 4);
  assert.deepEqual(results.slice(0, 2).map(r => r.record.path), ['core', 'other']);
});

test('空白、无匹配与没有目标语言页面时不会显示错语言记录', () => {
  assert.deepEqual(search.search(bilingual, '  ', 'zh'), []);
  assert.deepEqual(search.search(bilingual, 'unmatched', 'zh'), []);
  assert.deepEqual(search.search(bilingual.filter(r => r.language === 'en'), 'Stress', 'zh'), []);
});
