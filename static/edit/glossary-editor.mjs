import { parseGlossary, serializeGlossary, newTerm, invalidateReview, reviewHash } from "../js/glossary-core.mjs?v=20260926c";

export function createGlossaryEditor(container, { onChange, sources }) {
  let terms = [];
  let selected = "";
  let query = "";
  let pendingDelete = "";
  container.innerHTML = `
    <div class="glossary-toolbar"><div><h2>术语表</h2><p id="glossary-count"></p></div><button type="button" class="secondary-button" id="glossary-new">新增术语</button><button type="button" class="secondary-button" id="glossary-markdown">编辑 Markdown</button></div>
    <p id="glossary-error" role="status"></p>
    <div class="glossary-layout">
      <aside class="glossary-list-pane"><label>查找术语<input id="glossary-search" type="search" placeholder="中文、英文或别名"></label><div id="glossary-list"></div></aside>
      <div id="glossary-detail"></div>
    </div>`;
  const list = container.querySelector("#glossary-list");
  const detail = container.querySelector("#glossary-detail");
  const error = container.querySelector("#glossary-error");
  function element(tag, text) { const item = document.createElement(tag); if (text !== undefined) item.textContent = text; return item; }
  function current() { return terms.find((term) => term.id === selected); }
  function save() {
    try {
      onChange(serializeGlossary(terms)); error.textContent = ""; renderList();
      detail.querySelectorAll(".glossary-review-status").forEach((status) => {
        const definition = current()?.definition[status.dataset.language];
        if (definition) status.textContent = definition.mode === "approved" ? `已审核 · ${definition.reviewer} · ${definition.reviewedAt}` : definition.mode === "quote" ? "原文摘录 · 发布时与来源逐字核对" : "待审核 · 启用前请引用原文或人工审核";
      });
    }
    catch (exception) { error.textContent = exception.message; }
  }
  function renderList() {
    container.querySelector("#glossary-count").textContent = `${terms.length} 条术语 · ${terms.filter((term) => term.enabled).length} 条启用`;
    list.replaceChildren();
    const matches = terms.filter((term) => [term.zh, term.en, ...term.aliases.zh, ...term.aliases.en].join(" ").toLowerCase().includes(query.toLowerCase()));
    for (const term of matches) {
      const button = element("button"); button.type = "button";
      button.className = term.id === selected ? "selected" : "";
      button.setAttribute("aria-pressed", String(term.id === selected));
      button.append(element("b", term.zh || "未命名"), element("small", `${term.en || "未填写英文"} · ${term.enabled ? "启用" : "停用"}`));
      button.addEventListener("click", () => { selected = term.id; pendingDelete = ""; renderList(); renderDetail(); });
      list.append(button);
    }
    if (!matches.length) list.append(element("p", "没有匹配的术语"));
  }
  function field(parent, title, value, onInput, { multiline = false, type = "text", id = "" } = {}) {
    const label = element("label", title);
    const input = element(multiline ? "textarea" : "input");
    if (!multiline) input.type = type;
    if (id) input.id = id;
    if (type === "checkbox") input.checked = value; else input.value = value;
    input.addEventListener("input", () => { onInput(type === "checkbox" ? input.checked : input.value); save(); });
    label.append(input); parent.append(label); return input;
  }
  function select(parent, title, options, value, onChangeValue) {
    const label = element("label", title); const input = element("select");
    for (const [key, text] of options) { const option = element("option", text); option.value = key; input.append(option); }
    input.value = value;
    input.addEventListener("change", () => onChangeValue(input.value));
    label.append(input); parent.append(label); return input;
  }
  function renderDetail() {
    detail.replaceChildren();
    const term = current();
    if (!term) { detail.append(element("p", "选择左侧术语，或新增一条。")); return; }
    const heading = element("div"); heading.className = "glossary-detail-heading";
    heading.append(element("h3", "术语内容"), element("small", `标识：${term.id}`)); detail.append(heading);
    const basics = element("div"); basics.className = "glossary-fields"; detail.append(basics);
    const rename = (key, value) => { term[key] = value; for (const lang of ["zh", "en"]) invalidateReview(term, lang); };
    field(basics, "中文名称", term.zh, (value) => rename("zh", value), { id: "glossary-zh" });
    field(basics, "英文名称", term.en, (value) => rename("en", value), { id: "glossary-en" });
    field(basics, "中文别名（用；分隔）", term.aliases.zh.join("；"), (value) => { term.aliases.zh = value.split("；").map((part) => part.trim()).filter(Boolean); });
    field(basics, "英文别名（用；分隔）", term.aliases.en.join("；"), (value) => { term.aliases.en = value.split("；").map((part) => part.trim()).filter(Boolean); });
    field(basics, "区分英文大小写", term.case_sensitive, (value) => { term.case_sensitive = value; }, { type: "checkbox" });
    field(basics, "启用读者提示", term.enabled, (value) => { term.enabled = value; }, { type: "checkbox", id: "glossary-enabled" });
    field(detail, "翻译备注（不显示为规则解释）", term.note, (value) => { term.note = value; }, { multiline: true });
    const pageOptions = [["", "选择规则来源页面"], ...Object.entries(sources).map(([path, page]) => [path, page.title.zh])];
    if (term.target && !sources[term.target]) pageOptions.push([term.target, `来源待核对：${term.target}`]);
    select(detail, "规则来源", pageOptions, term.target, (value) => {
      term.target = value;
      for (const lang of ["zh", "en"]) { term.anchor[lang] = ""; invalidateReview(term, lang); }
      save(); renderDetail();
    });
    for (const [language, title] of [["zh", "中文"], ["en", "英文"]]) renderLanguage(term, language, title);
    const remove = element("button", pendingDelete === term.id ? "确认删除这条术语" : "删除术语");
    remove.type = "button"; remove.className = "secondary-button glossary-delete";
    remove.addEventListener("click", () => {
      if (pendingDelete !== term.id) { pendingDelete = term.id; remove.textContent = "确认删除这条术语"; return; }
      terms = terms.filter((item) => item.id !== term.id); selected = terms[0]?.id || ""; pendingDelete = "";
      save(); renderDetail();
    });
    detail.append(remove, element("p", "新增、删除和修改暂存在当前会话，点击上方“保存并发布”后才会生效。"));
  }
  function renderLanguage(term, language, title) {
    const section = element("section"); section.className = "glossary-language";
    section.append(element("h4", `${title}解释`)); detail.append(section);
    const definition = term.definition[language];
    const headings = sources[term.target]?.languages?.[language] || [];
    const headingOptions = [["", "选择对应小节"], ...headings.map((heading) => [heading.anchor, heading.title])];
    if (term.anchor[language] && !headings.some((heading) => heading.anchor === term.anchor[language])) headingOptions.push([term.anchor[language], `小节待核对：${term.anchor[language]}`]);
    select(section, `${title}来源小节`, headingOptions, term.anchor[language], (value) => {
      term.anchor[language] = value; invalidateReview(term, language); save(); renderDetail();
    });
    const blocks = headings.find((heading) => heading.anchor === term.anchor[language])?.blocks || [];
    if (blocks.length) {
      const range = element("div"); range.className = "glossary-fields"; section.append(range);
      const choices = blocks.map((block, index) => [String(index), `${index + 1}. ${block.slice(0, 48)}${block.length > 48 ? "…" : ""}`]);
      let start = 0; let end = 0;
      select(range, "摘录开始段落", choices, "0", (value) => { start = Number(value); });
      select(range, "摘录结束段落", choices, "0", (value) => { end = Number(value); });
      const quote = element("button", "引用所选原文"); quote.type = "button"; quote.className = "secondary-button";
      quote.addEventListener("click", () => {
        if (end < start) { error.textContent = "结束段落不能在开始段落之前"; return; }
        term.quote[language] = blocks.slice(start, end + 1).join("\n\n");
        invalidateReview(term, language); definition.mode = "quote"; save(); renderDetail();
      });
      section.append(quote);
    }
    const status = element("p"); status.className = "glossary-review-status";
    status.dataset.language = language;
    const updateStatus = () => { status.textContent = definition.mode === "approved" ? `已审核 · ${definition.reviewer} · ${definition.reviewedAt}` : definition.mode === "quote" ? "原文摘录 · 发布时与来源逐字核对" : "待审核 · 启用前请引用原文或人工审核"; };
    const explanation = field(section, `${title}解释正文`, term.quote[language], (value) => {
      term.quote[language] = value; invalidateReview(term, language); if (definition.mode !== "quote") definition.mode = "pending"; updateStatus();
    }, { multiline: true, id: `glossary-quote-${language}` });
    explanation.rows = 6; updateStatus(); section.append(status);
    const review = element("details"); review.className = "glossary-review";
    review.append(element("summary", "人工审核改写文案"));
    review.append(element("p", "仅在你已经逐字审核上面的解释后使用。之后修改名称、来源或解释，审核记录会失效。"));
    const reviewerLabel = element("label", "审核人"); const reviewer = element("input"); reviewer.autocomplete = "name"; reviewerLabel.append(reviewer); review.append(reviewerLabel);
    const approval = element("button", "我已审核，批准此文案"); approval.type = "button"; approval.className = "secondary-button";
    approval.addEventListener("click", async () => {
      if (!reviewer.value.trim() || !term.quote[language].trim()) { error.textContent = "请填写审核人及解释正文"; return; }
      const before = JSON.stringify(term);
      let hash;
      try { hash = await reviewHash(term, language); }
      catch (_) { error.textContent = "当前浏览器不能生成审核记录，请使用 HTTPS 网站或本机预览"; return; }
      if (JSON.stringify(term) !== before) { error.textContent = "文案刚刚发生变化，请重新审核"; return; }
      Object.assign(definition, { mode: "approved", reviewer: reviewer.value.trim(), reviewedAt: new Date().toISOString().slice(0, 10), hash });
      save(); renderDetail();
    });
    review.append(approval); section.append(review);
  }
  container.querySelector("#glossary-search").addEventListener("input", (event) => { query = event.target.value; renderList(); });
  container.querySelector("#glossary-new").addEventListener("click", () => {
    const term = newTerm(); terms.unshift(term); selected = term.id; query = "";
    container.querySelector("#glossary-search").value = ""; save(); renderDetail(); container.querySelector("#glossary-zh")?.focus();
  });
  return {
    setSources(next) { sources = next; renderDetail(); },
    load(markdown) {
      try { terms = parseGlossary(markdown).terms; selected = terms.some((term) => term.id === selected) ? selected : terms[0]?.id || ""; error.textContent = ""; container.querySelector("#glossary-new").disabled = false; renderList(); renderDetail(); return true; }
      catch (exception) { error.textContent = `Markdown 格式错误：${exception.message}。请切换 Markdown 修正。`; detail.replaceChildren(); list.replaceChildren(); container.querySelector("#glossary-new").disabled = true; return false; }
    },
  };
}
