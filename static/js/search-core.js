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
    return records
      .filter((record) => record.language === language)
      .map((record) => ({ record, score: scoreRecord(record, query, terms) }))
      .filter((item) => item.score >= 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }

  return { normalize, scoreRecord, search };
});
