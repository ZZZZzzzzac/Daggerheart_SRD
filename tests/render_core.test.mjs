import test from "node:test";
import assert from "node:assert/strict";

import { renderPair } from "../static/js/render-core.mjs";


test("one render core gives bilingual headings the same stable anchors", () => {
  const rendered = renderPair(
    "# 游戏\n\n## 动作掷骰\n\n获得 1 希望点。",
    "# Game\n\n## Action Roll\n\nGain 1 Hope.",
  );

  assert.deepEqual(rendered.anchors.zh, ["game", "action-roll"]);
  assert.deepEqual(rendered.anchors.en, ["game", "action-roll"]);
  assert.match(rendered.html.zh, /id="action-roll" data-anchor="action-roll"/);
  assert.match(rendered.html.en, /<h2 data-anchor="action-roll">Action Roll<\/h2>/);
  assert.match(rendered.html.zh, /<strong>获得 1 希望点<\/strong>/);
});


test("render core handles formal tables and Markdown inside sage blocks", () => {
  const source = [
    '<div class="sage-touched">',
    "<details>",
    "<summary>贤者恩泽</summary>",
    "",
    "这里有 **重点**。",
    "</details>",
    "</div>",
    "",
    "| 名称 | 很长的说明 |",
    "| --- | --- |",
    "| 测试 | 内容 |",
  ].join("\n");
  const rendered = renderPair(source, source);

  assert.match(rendered.html.zh, /<div class="sage-touched">/);
  assert.match(rendered.html.zh, /<strong>重点<\/strong>/);
  assert.match(rendered.html.zh, /<div class="table-scroll" role="region">\s*<table>/);
});


test("domain card pages render cards without changing ordinary level-four sections", () => {
  const source = [
    '## <img src="/SRD/img/domains/arcana.png" class="domain-icon" alt=""> 奥术领域 ARCANA',
    "",
    "#### 符文护符 RUNE WARD",
    "**1 级 奥术 法术 回想费用：0**  ",
    "卡牌正文第一行。",
    "卡牌正文第二行。",
    "",
    "#### 释放混沌 UNLEASH CHAOS",
    "**1 级 奥术 法术 回想费用：1**  ",
    "另一张卡牌。",
  ].join("\n");

  const cards = renderPair(source, source, { pagePath: "domain-cards" });
  const ordinary = renderPair(source, source);

  assert.match(cards.html.zh, /<section class="domain-section">/);
  assert.equal((cards.html.zh.match(/<article class="domain-card">/g) || []).length, 2);
  assert.match(cards.html.zh, /<div class="domain-card-grid">/);
  assert.match(cards.html.zh, /卡牌正文第一行。<br>\s*卡牌正文第二行。/);
  assert.doesNotMatch(ordinary.html.zh, /class="domain-card"/);
  assert.doesNotMatch(ordinary.html.zh, /卡牌正文第一行。<br>/);
});
