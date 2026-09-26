import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { parseGlossary, serializeGlossary, newTerm } from "../static/js/glossary-core.mjs";

test("seven fields preserve all 328 terms and Chinese explanations", () => {
  const markdown = readFileSync(new URL("../data/glossary.md", import.meta.url), "utf8");
  const glossary = parseGlossary(markdown);
  assert.equal(glossary.terms.length, 328);
  assert.deepEqual(parseGlossary(serializeGlossary(glossary.terms)), glossary);
  assert.deepEqual(Object.keys(glossary.terms[0]).sort(), ["en", "zh", "aliases", "case_sensitive", "description", "url"].sort());
  assert.match(glossary.terms.find(term => term.en === "Stress").description, /^压力点 代表/);
  assert.doesNotMatch(markdown, /^- .*审核|^- 读者提示|^### 英文解释|\{#/m);
});
test("new entries and empty descriptions need no workflow metadata", () => {
  const term = newTerm(); term.en = "Test"; term.zh = "测试";
  assert.deepEqual(parseGlossary(serializeGlossary([term])).terms[0], term);
  assert.equal(parseGlossary(serializeGlossary([])).terms.length, 0);
});
test("malformed fields fail clearly while duplicate imported names remain maintainable", () => {
  const term = newTerm(); const text = serializeGlossary([term]);
  assert.throws(() => parseGlossary(text.replace("- 大小写：不区分", "- 大小写：maybe")), /大小写/);
  assert.throws(() => parseGlossary(text.replace("- 跳转链接：\n", "")), /缺少字段/);
  assert.equal(parseGlossary(serializeGlossary([term, term])).terms.length, 2);
});
