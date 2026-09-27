import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { parseGlossary, serializeGlossary, newTerm } from "../static/js/glossary-core.mjs";

test("Chinese fields and section categories survive a Markdown round trip", () => {
  const markdown = readFileSync(new URL("../data/glossary.md", import.meta.url), "utf8");
  const glossary = parseGlossary(markdown);
  assert.ok(glossary.terms.length > 0);
  assert.deepEqual(parseGlossary(serializeGlossary(glossary.terms)), glossary);
  assert.deepEqual(Object.keys(glossary.terms[0]).filter(key => key !== "category").sort(), ["zh", "description", "url"].sort());
  assert.doesNotMatch(markdown, /^- .*审核|^- 读者提示|^### 英文解释|\{#/m);
});

test("category headings never become part of a Chinese explanation", () => {
  const first = { ...newTerm(), zh: "第一条", category: "游戏术语/概念/机制", description: "原有解释" };
  const second = { ...newTerm(), zh: "第二条", category: "自定义分区" };
  const parsed = parseGlossary(serializeGlossary([first, second]));
  assert.deepEqual(parsed.terms, [first, second]);
  assert.equal(parsed.terms[0].description, "原有解释");
});
test("new entries and empty descriptions need no workflow metadata", () => {
  const term = newTerm(); term.zh = "测试";
  assert.deepEqual(parseGlossary(serializeGlossary([term])).terms[0], term);
  assert.equal(parseGlossary(serializeGlossary([])).terms.length, 0);
});

test("term names ignore trailing whitespace when parsed and saved", () => {
  const term = { ...newTerm(), zh: "秽野之息 \t　" };
  const saved = serializeGlossary([term]);
  assert.match(saved, /## 中文名：秽野之息\n/);
  const manuallyEdited = saved.replace("## 中文名：秽野之息\n", "## 中文名：秽野之息 \t　\n");
  assert.equal(parseGlossary(manuallyEdited).terms[0].zh, "秽野之息");
});
test("malformed fields fail clearly while duplicate imported names remain maintainable", () => {
  const term = newTerm(); const text = serializeGlossary([term]);
  assert.throws(() => parseGlossary(text.replace("- 跳转链接：", "- 中文别名：")), /未知/);
  assert.throws(() => parseGlossary(text.replace("- 跳转链接：\n", "")), /缺少字段/);
  assert.equal(parseGlossary(serializeGlossary([term, term])).terms.length, 2);
});
