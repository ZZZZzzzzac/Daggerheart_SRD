import { parseGlossary, serializeGlossary, newTerm } from "../js/glossary-core.mjs?v=20260927a";

export function createGlossaryEditor(container, { onChange }) {
  let terms = [], selected = 0, query = "", confirmDelete = false;
  container.innerHTML = `<div class="glossary-toolbar"><div><h2>术语表</h2><p id="glossary-count"></p></div><button type="button" class="secondary-button" id="glossary-new">新增术语</button><button type="button" class="secondary-button" id="glossary-markdown">编辑 Markdown</button></div><p id="glossary-error" role="status"></p><div class="glossary-layout"><aside class="glossary-list-pane"><label>查找术语<input id="glossary-search" type="search" placeholder="术语名称"></label><div id="glossary-list"></div></aside><div id="glossary-detail"></div></div>`;
  const list = container.querySelector("#glossary-list"), detail = container.querySelector("#glossary-detail"), error = container.querySelector("#glossary-error");
  function element(tag, text) { const item = document.createElement(tag); if (text !== undefined) item.textContent = text; return item; }
  function save() {
    try { onChange(serializeGlossary(terms)); error.textContent = ""; renderList(); }
    catch (exception) { error.textContent = exception.message; }
  }
  function renderList() {
    container.querySelector("#glossary-count").textContent = `${terms.length} 条术语`;
    list.replaceChildren();
    let previousCategory;
    terms.forEach((term, index) => {
      if (!term.zh.toLowerCase().includes(query.toLowerCase())) return;
      if (term.category && term.category !== previousCategory) {
        const heading = element("h3", term.category); heading.className = "glossary-category"; list.append(heading);
        previousCategory = term.category;
      }
      const button = element("button"); button.type = "button"; button.className = index === selected ? "selected" : "";
      button.setAttribute("aria-pressed", String(index === selected));
      button.append(element("b", term.zh || "未填写中文名"));
      button.addEventListener("click", () => { selected = index; confirmDelete = false; renderList(); renderDetail(); });
      list.append(button);
    });
    if (!list.childElementCount) list.append(element("p", "没有匹配的术语"));
  }
  function field(parent, title, value, update, id, multiline = false) {
    const label = element("label", title), input = element(multiline ? "textarea" : "input");
    input.id = id; input.value = value;
    if (multiline) input.rows = 9;
    input.addEventListener("input", () => { update(input.value); save(); });
    label.append(input); parent.append(label);
  }
  function renderDetail() {
    detail.replaceChildren();
    const term = terms[selected];
    if (!term) { detail.append(element("p", "选择一条术语，或新增术语。")); return; }
    const basics = element("div"); basics.className = "glossary-fields"; detail.append(basics);
    field(basics, "中文名", term.zh, value => { term.zh = value; }, "glossary-zh");
    field(detail, "中文解释", term.description, value => { term.description = value; }, "glossary-description", true);
    field(detail, "跳转链接", term.url, value => { term.url = value; }, "glossary-url");
    const remove = element("button", confirmDelete ? "确认删除这条术语" : "删除术语"); remove.type = "button"; remove.className = "secondary-button glossary-delete";
    remove.addEventListener("click", () => {
      if (!confirmDelete) { confirmDelete = true; remove.textContent = "确认删除这条术语"; return; }
      terms.splice(selected, 1); selected = Math.min(selected, terms.length - 1); confirmDelete = false; save(); renderDetail();
    });
    detail.append(remove);
  }
  container.querySelector("#glossary-search").addEventListener("input", event => { query = event.target.value; renderList(); });
  container.querySelector("#glossary-new").addEventListener("click", () => {
    if (terms.some(term => term.category)) { terms.push({ ...newTerm(), category: "备用区" }); selected = terms.length - 1; }
    else { terms.unshift(newTerm()); selected = 0; }
    query = ""; confirmDelete = false; container.querySelector("#glossary-search").value = ""; save(); renderDetail();
  });
  return { load(markdown) {
    try { terms = parseGlossary(markdown).terms; selected = Math.max(0, Math.min(selected, terms.length - 1)); error.textContent = ""; container.querySelector("#glossary-new").disabled = false; renderList(); renderDetail(); }
    catch (exception) { error.textContent = `Markdown 格式错误：${exception.message}。请切换 Markdown 修正。`; list.replaceChildren(); detail.replaceChildren(); container.querySelector("#glossary-new").disabled = true; }
  } };
}
