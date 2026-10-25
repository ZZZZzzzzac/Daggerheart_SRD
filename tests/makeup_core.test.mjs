import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { transformProse, formatResourcePhrases, replaceKeywords } from '../static/js/makeup-core.mjs';
import { renderPair } from '../static/js/render-core.mjs';

const fixture = JSON.parse(readFileSync(new URL('./fixtures/makeup-cases.json', import.meta.url), 'utf8'));
const normalize = source => transformProse(source, text => formatResourcePhrases(replaceKeywords(text), {bold: false}));
test('resource rules agree with Python normalization and are idempotent', () => {
  for (const [source, expected] of fixture.cases) {
    assert.equal(normalize(source), expected, source);
    assert.equal(normalize(expected), expected, source);
  }
  for (const source of fixture.unchanged) assert.equal(normalize(source), source, source);
});

test('rendering preserves armor scores, dice names, abbreviation definitions and narrative', () => {
  for (const source of ['获得1护甲值', '获得1希望骰', '获得1希望槽', '获得一种希望之光', '消耗敌人的生命', '清除所有生命点和压力点', '游戏主持人（“GM”），玩家角色（“PC”）']) {
    const text = renderPair(source, '').html.zh.replace(/<[^>]*>/g, '').replace(/\s/g, '');
    assert.equal(text, source.replace(/\s/g, ''));
  }
  assert.match(renderPair('恢复2d8+1生命点，恢复1压力点。', '').html.zh,
    /<strong>恢复 2d8\+1 生命点<\/strong>，<strong>清除 1 压力点<\/strong>/);
});

test('rendering retains code, links, images and anchor attributes', () => {
  const source = '`PC标记1生命点`\n\n```\nGM花费1希望点\n```\n\n[PC标记1生命点](https://example.com/PC1)\n\n![GM](card.png)\n\n<span id="PC1" data-anchor="PC1"></span>';
  const html = renderPair(source, '').html.zh;
  assert.match(html, /<code>PC标记1生命点<\/code>/);
  assert.match(html, /<pre><code>GM花费1希望点\n<\/code><\/pre>/);
  assert.match(html, /<a href="https:\/\/example.com\/PC1">PC标记1生命点<\/a>/);
  assert.match(html, /<img src="card.png" alt="GM">/);
  assert.match(html, /id="PC1" data-anchor="PC1"/);
});
