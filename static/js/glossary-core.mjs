const preamble = "# 术语表\n\n别名用中文分号（；）分隔。大小写填写“区分”或“不区分”。中文解释和跳转链接可留空。\n";
const fields = ["中文名", "中文别名", "英文别名", "大小写", "跳转链接"];
export function newTerm() {
  return { en: "New Term", zh: "新术语", aliases: { zh: [], en: [] }, case_sensitive: false, description: "", url: "" };
}
export function parseGlossary(markdown) {
  const terms = [];
  let term, metadata, explanation = false, lines = [];
  function finish() {
    if (!term) return;
    for (const field of fields) if (!metadata.has(field)) throw new Error(`${term.en} 缺少字段：${field}`);
    if (!explanation) throw new Error(`${term.en} 缺少“中文解释”小节`);
    term.description = lines.join("\n").trim();
  }
  for (const line of markdown.replace(/\r\n?/g, "\n").split("\n")) {
    if (line.startsWith("## ")) {
      finish();
      const match = line.match(/^## 英文名：\s*(.+)$/);
      if (!match) throw new Error("术语标题应为：## 英文名：Hope");
      term = newTerm(); term.en = match[1].trim(); terms.push(term);
      metadata = new Set(); explanation = false; lines = [];
    } else if (term && line === "### 中文解释") {
      if (explanation) throw new Error(`${term.en} 重复的中文解释小节`);
      explanation = true;
    } else if (term && explanation) {
      lines.push(line);
    } else if (term && line.trim()) {
      const match = line.match(/^- ([^：]+)：\s*(.*)$/);
      if (!match || !fields.includes(match[1]) || metadata.has(match[1])) throw new Error(`${term.en} 未知或重复字段：${line}`);
      const [, name, value] = match; metadata.add(name);
      if (name === "中文名") term.zh = value;
      else if (name === "跳转链接") term.url = value;
      else if (name === "大小写") {
        if (!["区分", "不区分"].includes(value)) throw new Error("大小写应填写“区分”或“不区分”");
        term.case_sensitive = value === "区分";
      } else term.aliases[name === "中文别名" ? "zh" : "en"] = value.split("；").map(item => item.trim()).filter(Boolean);
    }
  }
  finish();
  return { terms };
}
export function serializeGlossary(terms) {
  function single(value) {
    if (/[\r\n]/.test(value || "")) throw new Error("名称、别名和链接不能包含换行");
    return value || "";
  }
  return preamble + terms.map(term => `\n## 英文名：${single(term.en)}\n\n- 中文名：${single(term.zh)}\n- 中文别名：${single(term.aliases.zh.join("；"))}\n- 英文别名：${single(term.aliases.en.join("；"))}\n- 大小写：${term.case_sensitive ? "区分" : "不区分"}\n- 跳转链接：${single(term.url)}\n\n### 中文解释\n\n${term.description.trim()}\n`).join("");
}
