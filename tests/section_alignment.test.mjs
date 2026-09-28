import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { renderPair } from '../static/js/render-core.mjs';
import { legacyAnchors } from '../static/js/legacy-anchors.mjs';

const pages = new URL('../src/pages/', import.meta.url);
const paths = readdirSync(pages, { recursive: true }).filter(p => /[\\/]zh\.md$/.test(p)).map(p => p.replaceAll('\\', '/').slice(0, -6));
const results = new Map(paths.map(path => [path, renderPair(...['zh', 'en'].map(lang => readFileSync(new URL(`${path}/${lang}.md`, pages), 'utf8')), { pagePath: path })]));

test('同一小节锚点连接正确的双语内容，不受额外标题影响', () => {
  for (const [path, zh, en] of [
    ['core-resources/domains', '利刃', 'BLADE'],
    ['core-resources/classes', '德鲁伊', 'DRUID'],
    ['running-a-game', '游戏主持人实践', 'GM PRACTICES'],
    ['core-resources/classes', '基础特性', 'FOUNDATION FEATURE'],
    ['core-resources/classes', '法师', 'WIZARD'],
    ['core-resources/domains', '奥术', 'ARCANA'],
    ['campaign-frames', '秽野之息', 'The Witherwild'],
    ['running-a-game', '分阶段战斗', 'PHASED BATTLES'],
    ['running-a-game', '1d12 目标', '1d12 Objective'],
  ]) {
    const result = results.get(path);
    const chinese = result.headings.zh.find(h => h.title === zh);
    const english = result.headings.en.find(h => h.title === en);
    assert.ok(chinese && english, path);
    assert.equal(chinese.anchor, english.anchor, `${path}: ${zh} ↔ ${en}`);
  }
});

test('全站小节都有显式唯一锚点，旧链接不会覆盖新锚点或丢失', () => {
  for (const [path, result] of results) {
    for (const lang of ['zh', 'en']) {
      const anchors = new Set(result.anchors[lang]);
      assert.equal(anchors.size, result.headings[lang].length, path);
      for (const h of result.headings[lang]) {
        assert.match(h.raw, /\{#[a-z][\w-]*\}$/, `${path}: ${h.raw}`);
        assert.equal((h.raw.match(/\{#/g) || []).length, 1, h.raw);
      }
      for (const [old, target] of Object.entries(legacyAnchors[path]?.[lang] || {})) {
        assert.ok(!anchors.has(old), `${path}: ${old} 覆盖新锚点`);
        assert.ok(anchors.has(target), `${path}: ${old} 目标不存在`);
        assert.ok(result.html[lang].includes(`data-legacy-anchor="${old}" data-target-anchor="${target}"`), `${path}: ${old} 别名丢失`);
      }
    }
  }
});

test('敌人与环境卡内标题按卡片身份配对，不依赖卡片顺序', () => {
  for (const kind of ['adversary', 'environment']) {
    const path = `adversaries-and-environments/${kind}-data`;
    for (const lang of ['zh', 'en']) {
      const text = readFileSync(new URL(`${path}/${lang}.md`, pages), 'utf8');
      const blocks = [...text.matchAll(new RegExp(`<!-- ${kind}: ([^|]+) \\| .*? -->([\\s\\S]*?)<!-- /${kind} -->`, 'g'))];
      for (const [, rawId, content] of blocks) {
        const id = rawId.trim();
        const title = content.match(/^#{1,6} .+$/m)?.[0];
        assert.ok(title.endsWith(`{#section-${kind}-${id}}`), `${path}: ${id}`);
        const features = content.match(/^#{1,6} \*\*(?:特性|FEATURES)\*\* .+$/m)?.[0];
        if (features) assert.ok(features.endsWith(`{#section-${kind}-${id}-features}`));
      }
    }
  }
});

test('单语独有标题保留独立身份，不与其他语言无关小节配对', () => {
  for (const [path, language, anchor] of [
    ['core-resources/domains', 'zh', 'section-loadout-and-vault'],
    ['core-resources/classes', 'en', 'section-spellcast-trait'],
    ['running-a-game', 'en', 'section-examples'],
  ]) {
    const result = results.get(path);
    assert.ok(result.anchors[language].includes(anchor));
    assert.ok(!result.anchors[language === 'zh' ? 'en' : 'zh'].includes(anchor));
  }
});
