(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.SrdSearch = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function normalize(value) {
    return String(value || "").toLocaleLowerCase().replace(/\s+/g, " ").trim();
  }

  function scoreRecord(record, query, terms) {
    const pageTitle = normalize(record.pageTitle);
    const heading = normalize(record.heading);
    const content = normalize(record.body);
    const combined = `${pageTitle} ${heading} ${content}`;
    if (!terms.every((term) => combined.includes(term))) return -1;
    let score = 0;
    if (pageTitle === query) score += 1800;
    else if (pageTitle.includes(query)) score += 1200;
    if (heading === query) score += 1100;
    else if (heading.includes(query)) score += 700;
    terms.forEach((term) => {
      if (pageTitle.includes(term)) score += 220;
      if (heading.includes(term)) score += 120;
      if (content.includes(term)) score += 20;
    });
    return score;
  }

  function search(records, rawQuery, language, limit = 50) {
    const query = normalize(rawQuery);
    if (!query) return [];
    const terms = query.split(" ").filter(Boolean);
    const keyFor = (record) => `${record.path}#${record.anchor}`;
    const translated = new Map();
    const pages = new Map();
    records.filter((record) => record.language === language).forEach((record) => {
      translated.set(keyFor(record), record);
      if (!pages.has(record.path)) pages.set(record.path, record.pageTitle);
    });
    const matches = new Map();
    records.forEach((sourceRecord) => {
      const score = scoreRecord(sourceRecord, query, terms);
      if (score < 0) return;
      let record = translated.get(keyFor(sourceRecord));
      const chapterOnly = !record;
      if (!record) {
        const title = pages.get(sourceRecord.path);
        if (!title) return;
        // 另一语言没有同一小节时只定位章节，不猜测相邻小节的含义。
        record = { path: sourceRecord.path, anchor: "top", language, pageTitle: title, heading: title, body: "" };
      }
      const key = keyFor(record);
      const previous = matches.get(key);
      if (!previous || score > previous.score || (score === previous.score && sourceRecord.language === language && previous.sourceRecord.language !== language)) {
        matches.set(key, { record, score, sourceRecord, chapterOnly });
      }
    });
    return [...matches.values()]
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }

  return { normalize, scoreRecord, search };
});
