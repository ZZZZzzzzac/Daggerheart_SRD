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

test("search stays inside the selected language", () => {
  assert.equal(search.search(records, "Action Roll", "zh").length, 0);
  assert.equal(search.search(records, "Action Roll", "en")[0].record.anchor, "d");
});

test("search does not guess misspellings", () => {
  assert.equal(search.search(records, "动做掷骰", "zh").length, 0);
});
