const preamble = "# 术语表\n\n中文解释和跳转链接可留空。\n";
const fields = ["跳转链接"];
export const categories = ["游戏术语/概念/机制", "游戏资源/种族/职业/社群", "剧情/设定/战役框架", "状态", "备用区"];
export function newTerm() {
  return { zh: "新术语", description: "", url: "" };
}
export function parseGlossary(markdown) {
  const terms = [];
  let term, metadata, explanation = false, lines = [], category;
  function finish() {
    if (!term) return;
    for (const field of fields) if (!metadata.has(field)) throw new Error(`${term.zh} 缺少字段：${field}`);
    if (!explanation) throw new Error(`${term.zh} 缺少“中文解释”小节`);
    term.description = lines.join("\n").trim();
  }
  for (const line of markdown.replace(/\r\n?/g, "\n").split("\n")) {
    if (line.startsWith("# ") && line.slice(2).trim() !== "术语表") {
      finish(); term = null; lines = []; explanation = false;
      category = line.slice(2).trim();
    } else if (line.startsWith("## ")) {
      finish();
      const match = line.match(/^## 中文名：\s*(.+)$/);
      if (!match) throw new Error("术语标题应为：## 中文名：希望点");
      term = newTerm(); term.zh = match[1].trimEnd(); terms.push(term);
      if (category) term.category = category;
      metadata = new Set(); explanation = false; lines = [];
    } else if (term && line === "### 中文解释") {
      if (explanation) throw new Error(`${term.zh} 重复的中文解释小节`);
      explanation = true;
    } else if (term && explanation) {
      lines.push(line);
    } else if (term && line.trim()) {
      const match = line.match(/^- ([^：]+)：\s*(.*)$/);
      if (!match || !fields.includes(match[1]) || metadata.has(match[1])) throw new Error(`${term.zh} 未知或重复字段：${line}`);
      const [, name, value] = match; metadata.add(name);
      if (name === "跳转链接") term.url = value;
    }
  }
  finish();
  return { terms };
}
export function serializeGlossary(terms) {
  function single(value) {
    if (/[\r\n]/.test(value || "")) throw new Error("名称和链接不能包含换行");
    return value || "";
  }
  const grouped = terms.some(term => term.category);
  let previousCategory;
  return preamble + terms.map(term => {
    const category = term.category || "备用区";
    const heading = grouped && category !== previousCategory ? `\n# ${single(category)}\n` : "";
    previousCategory = category;
    return heading + `\n## 中文名：${single(term.zh).trimEnd()}\n- 跳转链接：${single(term.url)}\n### 中文解释\n${term.description.trim()}\n`;
  }).join("");
}
