import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { parseGlossary, serializeGlossary, newTerm, reviewHash, invalidateReview } from "../static/js/glossary-core.mjs";

test("the editable Markdown preserves all imported terms and exact excerpts through a round trip", () => {
  const source = readFileSync(new URL("../data/glossary.md", import.meta.url), "utf8");
  const parsed = parseGlossary(source);
  assert.equal(parsed.terms.length, 328);
  assert.equal(parsed.terms.filter((term) => term.enabled).length, 14);
  assert.deepEqual(parseGlossary(serializeGlossary(parsed.terms)), parsed);
  assert.match(parsed.terms.find((term) => term.id === "stress").quote.zh, /^压力点 代表角色/);
});

test("adding and deleting entries is reflected in the shared Markdown", () => {
  const term = newTerm("custom-term");
  term.zh = "测试术语"; term.en = "Test Term";
  const parsed = parseGlossary(serializeGlossary([term]));
  assert.equal(parsed.terms[0].enabled, false);
  assert.equal(parsed.terms[0].definition.zh.mode, "pending");
  assert.equal(parseGlossary(serializeGlossary([])).terms.length, 0);
});

test("malformed metadata and duplicate identifiers cannot silently disappear", () => {
  const term = newTerm("test"); const source = serializeGlossary([term]);
  assert.throws(() => parseGlossary(source.replace("- 读者提示：停用", "- 读者提示：maybe")), /必须为/);
  assert.throws(() => parseGlossary(source.replace("### 中文解释", "### 中文改写")), /未知/);
  assert.throws(() => parseGlossary(source.replace("- 中文审核人：\n", "")), /缺少字段/);
  assert.throws(() => parseGlossary(serializeGlossary([term, term])), /重复术语标识/);
});

test("review fingerprints change when names, sources or explanation text change", async () => {
  const term = newTerm("review"); term.quote.zh = "人工文案";
  const original = await reviewHash(term, "zh");
  term.definition.zh = { mode: "approved", reviewer: "人工测试", reviewedAt: "2026-09-26", hash: original };
  term.quote.zh += "有修改";
  assert.notEqual(await reviewHash(term, "zh"), original);
  invalidateReview(term, "zh");
  assert.equal(term.definition.zh.mode, "pending");
  assert.equal(term.definition.zh.hash, "");
});
