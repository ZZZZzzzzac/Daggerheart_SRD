// The editor and the build CLI share this human-editable Markdown format.
const fields = {
  "英文": "en", "中文别名": "aliasesZh", "英文别名": "aliasesEn",
  "区分英文大小写": "caseSensitive", "读者提示": "enabled", "来源页面": "target",
  "中文小节": "anchorZh", "英文小节": "anchorEn",
  "中文解释类型": "modeZh", "英文解释类型": "modeEn",
  "中文审核人": "reviewerZh", "英文审核人": "reviewerEn",
  "中文审核日期": "reviewedAtZh", "英文审核日期": "reviewedAtEn",
  "中文审核指纹": "reviewHashZh", "英文审核指纹": "reviewHashEn",
};
const modes = { "原文": "quote", "待审核": "pending", "已审核": "approved" };
const modeLabels = Object.fromEntries(Object.entries(modes).map(([label, mode]) => [mode, label]));
const preamble = "# 规则术语表\n\n名称和译名初始导入自翻译词表 terms-14448.json。只启用有原文出处或已人工审核解释的条目。\n\n每个二级标题是一条术语；新增、修改、停用或删除条目后，可在网站 editor 保存并发布。翻译备注不作为规则解释。别名用中文分号（；）分隔。\n";

export function newTerm(id = `term-${crypto.randomUUID()}`) {
  return { id, zh: "新术语", en: "", aliases: { zh: [], en: [] }, case_sensitive: false, enabled: false,
    target: "", anchor: { zh: "", en: "" }, quote: { zh: "", en: "" }, note: "",
    definition: { zh: { mode: "pending", reviewer: "", reviewedAt: "", hash: "" }, en: { mode: "pending", reviewer: "", reviewedAt: "", hash: "" } } };
}

function list(value) { return value ? value.split("；").map((part) => part.trim()).filter(Boolean) : []; }

export function parseGlossary(markdown) {
  const terms = [];
  const ids = new Set();
  let current = null;
  let section = "";
  let lines = [];
  let metadata = new Set();
  let sections = new Set();
  function flush() {
    if (!current || !section) return;
    const text = lines.join("\n").trim();
    if (section === "翻译备注") current.note = text;
    else current.quote[section === "中文解释" ? "zh" : "en"] = text;
    lines = [];
  }
  function finish() {
    flush();
    if (current) {
      for (const name of Object.keys(fields)) if (!metadata.has(name)) throw new Error(`${current.id} 缺少字段：${name}`);
      for (const name of ["翻译备注", "中文解释", "英文解释"]) if (!sections.has(name)) throw new Error(`${current.id} 缺少小节：${name}`);
    }
  }
  for (const line of markdown.replace(/\r\n?/g, "\n").split("\n")) {
    if (/^## /.test(line)) {
      finish();
      const match = line.match(/^## (.+?) \{#([a-z][a-z0-9-]*)\}$/);
      if (!match) throw new Error("术语标题格式应为：## 中文名称 {#唯一标识}");
      if (ids.has(match[2])) throw new Error(`重复术语标识：${match[2]}`);
      ids.add(match[2]);
      current = newTerm(match[2]); current.zh = match[1];
      terms.push(current); metadata = new Set(); sections = new Set(); section = "";
    } else if (current && /^### /.test(line)) {
      flush();
      section = line.slice(4).trim();
      if (!["翻译备注", "中文解释", "英文解释"].includes(section) || sections.has(section)) throw new Error(`${current.id} 未知或重复小节：${section}`);
      sections.add(section);
    } else if (current && !section && line.trim()) {
      const match = line.match(/^- ([^：]+)：\s*(.*)$/);
      if (!match || !(match[1] in fields) || metadata.has(match[1])) throw new Error(`${current.id} 未知或重复字段：${line}`);
      const [, name, value] = match;
      metadata.add(name);
      if (name === "英文") current.en = value;
      else if (name === "中文别名") current.aliases.zh = list(value);
      else if (name === "英文别名") current.aliases.en = list(value);
      else if (name === "来源页面") current.target = value;
      else if (name === "读者提示") {
        if (!["启用", "停用"].includes(value)) throw new Error(`${current.id} 读者提示必须为启用或停用`);
        current.enabled = value === "启用";
      } else if (name === "区分英文大小写") {
        if (!["是", "否"].includes(value)) throw new Error(`${current.id} 大小写字段必须为是或否`);
        current.case_sensitive = value === "是";
      } else {
        const language = name.startsWith("中文") ? "zh" : "en";
        if (name.endsWith("小节")) current.anchor[language] = value;
        else if (name.endsWith("解释类型")) {
          if (!modes[value]) throw new Error(`${current.id} 未知解释类型：${value}`);
          current.definition[language].mode = modes[value];
        } else if (name.endsWith("审核人")) current.definition[language].reviewer = value;
        else if (name.endsWith("审核日期")) current.definition[language].reviewedAt = value;
        else current.definition[language].hash = value;
      }
    } else if (current && section) lines.push(line);
  }
  finish();
  return { enabled: true, terms };
}

export function serializeGlossary(terms) {
  function single(value) {
    if (/[\r\n]/.test(value || "")) throw new Error("名称、别名及元数据不能包含换行");
    return value || "";
  }
  return preamble + terms.map((term) => {
    const values = {
      "英文": term.en, "中文别名": term.aliases.zh.join("；"), "英文别名": term.aliases.en.join("；"),
      "区分英文大小写": term.case_sensitive ? "是" : "否", "读者提示": term.enabled ? "启用" : "停用", "来源页面": term.target,
      "中文小节": term.anchor.zh, "英文小节": term.anchor.en,
    };
    for (const [language, label] of [["zh", "中文"], ["en", "英文"]]) {
      const definition = term.definition[language];
      values[`${label}解释类型`] = modeLabels[definition.mode];
      values[`${label}审核人`] = definition.reviewer;
      values[`${label}审核日期`] = definition.reviewedAt;
      values[`${label}审核指纹`] = definition.hash;
    }
    return `\n## ${single(term.zh)} {#${single(term.id)}}\n\n${Object.entries(values).map(([key, value]) => `- ${key}：${single(value)}`).join("\n")}\n\n### 翻译备注\n\n${term.note || ""}\n\n### 中文解释\n\n${term.quote.zh}\n\n### 英文解释\n\n${term.quote.en}\n`;
  }).join("");
}

export function reviewPayload(term, language) {
  return [term.id, term.zh, term.en, term.target, term.anchor[language], term.quote[language]].join("\n");
}

export async function reviewHash(term, language) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(reviewPayload(term, language)));
  return [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function invalidateReview(term, language) {
  const definition = term.definition[language];
  if (definition.mode === "approved") definition.mode = "pending";
  Object.assign(definition, { reviewer: "", reviewedAt: "", hash: "" });
}
