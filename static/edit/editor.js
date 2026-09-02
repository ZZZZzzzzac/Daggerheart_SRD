(function () {
  "use strict";

  const state = {
    pages: {},
    site: null,
    slug: "",
    language: readSetting("dh-srd-lang", "zh") === "en" ? "en" : "zh",
    original: "",
    version: "",
    previewTimer: null,
    pendingAnchor: "",
  };
  const textarea = document.getElementById("editor-textarea");
  const status = document.getElementById("save-status");
  const saveButton = document.getElementById("save-btn");
  const displayName = document.getElementById("display-name");

  function readSetting(key, fallback) {
    try { return localStorage.getItem(key) || fallback; } catch (_) { return fallback; }
  }

  function saveSetting(key, value) {
    try { localStorage.setItem(key, value); } catch (_) { /* storage is optional */ }
  }

  function setStatus(message, error = false) {
    status.textContent = message;
    status.classList.toggle("error", error);
  }

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function textFor(value) {
    return value?.[state.language] || value?.zh || value?.en || "";
  }

  function isDirty() { return textarea.value !== state.original; }
  function updateSaveState() { saveButton.disabled = !state.slug || !isDirty(); }
  function currentPath() { return state.pages[state.slug]?.files?.[state.language]; }
  function canLeaveDocument() { return !isDirty() || window.confirm("当前修改尚未保存，确定放弃吗？"); }
  function readerUrl(path, anchor = "") { return `../${path}/${anchor ? `#${encodeURIComponent(anchor)}` : ""}`; }
  function editorUrl(path, language = state.language) { return `./?path=${encodeURIComponent(path)}&lang=${language}`; }

  async function request(url, options) {
    const response = await fetch(url, { credentials: "same-origin", ...options });
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(data.error || `HTTP ${response.status}`);
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  function pageMap() {
    return new Map((state.site?.pages || []).map((page) => [page.path, page]));
  }

  function summaryRow(title, path) {
    const row = node("span", "tree-summary-row");
    row.append(node("span", "tree-caret", "›"));
    const link = node("a", "tree-page-link", title);
    link.href = editorUrl(path);
    link.addEventListener("click", (event) => event.stopPropagation());
    row.append(link);
    return row;
  }

  function buildPageBranch(page) {
    const details = node("details", `tree-page${page.path === state.slug ? " current" : ""}`);
    details.open = page.path === state.slug;
    const summary = node("summary");
    summary.append(summaryRow(textFor(page.title), page.path));
    details.append(summary);
    const headings = page.headings?.[state.language] || [];
    if (headings.length) {
      const list = node("ul", "tree-headings");
      headings.forEach((heading) => {
        const item = node("li", `level-${heading.level}`);
        const link = node("a", "", heading.title);
        link.href = editorUrl(page.path, state.language) + `#${encodeURIComponent(heading.anchor)}`;
        item.append(link);
        list.append(item);
      });
      details.append(list);
    }
    return details;
  }

  function renderTree() {
    const container = document.getElementById("contents-tree");
    if (!state.site) return;
    container.replaceChildren();
    const pages = pageMap();
    const list = node("ul", "tree-list");
    state.site.tree.forEach((entry) => {
      const item = node("li");
      if (entry.type === "group") {
        const details = node("details", "tree-group");
        details.open = entry.children.includes(state.slug);
        const summary = node("summary");
        const row = node("span", "tree-summary-row");
        row.append(node("span", "tree-caret", "›"), node("span", "tree-title", textFor(entry.title)));
        summary.append(row);
        details.append(summary);
        const children = node("ul", "tree-children");
        entry.children.forEach((path) => {
          const page = pages.get(path);
          if (!page) return;
          const child = node("li");
          child.append(buildPageBranch(page));
          children.append(child);
        });
        details.append(children);
        item.append(details);
      } else {
        const page = pages.get(entry.path);
        if (page) item.append(buildPageBranch(page));
      }
      list.append(item);
    });
    container.append(list);
  }

  function inferReferrerPath() {
    try {
      const referrer = new URL(document.referrer);
      if (referrer.origin !== location.origin) return "";
      const base = new URL("../", location.href).pathname;
      const relative = decodeURIComponent(referrer.pathname).slice(base.length).replace(/^\/+|\/+$/g, "");
      return relative && !relative.startsWith("edit") && !relative.startsWith("admin") ? relative : "";
    } catch (_) { return ""; }
  }

  async function loadPages() {
    try {
      const [catalog, site] = await Promise.all([
        request("/SRD/api/page-list"),
        request(document.body.dataset.siteIndex),
      ]);
      catalog.pages.forEach((page) => { state.pages[page.path] = page; });
      state.site = site;
      const parameters = new URLSearchParams(location.search);
      const requestedLanguage = parameters.get("lang");
      if (requestedLanguage === "zh" || requestedLanguage === "en") state.language = requestedLanguage;
      const requestedPath = new URLSearchParams(location.search).get("path");
      const initialPath = state.pages[requestedPath]
        ? requestedPath
        : (state.pages[inferReferrerPath()] ? inferReferrerPath() : catalog.pages[0]?.path);
      renderTree();
      if (initialPath) await loadDocument(initialPath, state.language, decodeURIComponent(location.hash.slice(1)));
      else setStatus("没有可编辑的页面", true);
    } catch (error) {
      setStatus(`页面列表加载失败：${error.message}`, true);
      document.getElementById("contents-tree").textContent = "目录加载失败";
    }
  }

  function updatePageChrome() {
    const page = state.pages[state.slug];
    const title = textFor(page?.title) || state.slug;
    document.getElementById("editor-document-label").textContent = title;
    document.title = `${title} · SRD 编辑器`;
    document.querySelector(".editor-shell").dataset.pagePath = state.slug;
    document.getElementById("language-button").textContent = state.language === "zh" ? "中文" : "EN";
    document.documentElement.lang = state.language === "zh" ? "zh-CN" : "en";
    const url = readerUrl(state.slug);
    document.getElementById("reader-link").href = url;
    document.getElementById("sidebar-reader-link").href = url;
    history.replaceState(null, "", editorUrl(state.slug, state.language) + (state.pendingAnchor ? `#${encodeURIComponent(state.pendingAnchor)}` : ""));
    renderTree();
  }

  async function loadDocument(slug, language, anchor = "") {
    const path = state.pages[slug]?.files?.[language];
    if (!path) { setStatus("该语言文件不存在", true); return; }
    setStatus("加载中…");
    state.pendingAnchor = anchor;
    try {
      const data = await request(`/SRD/api/get-file?path=${encodeURIComponent(path)}`);
      state.slug = slug;
      state.language = language;
      state.original = data.content;
      state.version = data.version;
      textarea.value = data.content;
      textarea.disabled = false;
      document.getElementById("document-version").textContent = `版本 ${data.version}`;
      document.getElementById("conflict-panel").hidden = true;
      saveSetting("dh-srd-lang", language);
      updatePageChrome();
      updateSaveState();
      await renderPreview();
      setStatus("已载入");
      document.body.classList.remove("sidebar-open");
    } catch (error) { setStatus(`加载失败：${error.message}`, true); }
  }

  function schedulePreview() {
    clearTimeout(state.previewTimer);
    state.previewTimer = setTimeout(renderPreview, 280);
    document.getElementById("preview-status").textContent = "等待更新";
  }

  function scrollPreviewTo(anchor) {
    const heading = [...document.querySelectorAll("#preview [data-anchor]")].find((item) => item.dataset.anchor === anchor);
    heading?.scrollIntoView({ block: "start" });
    if (anchor) history.replaceState(null, "", editorUrl(state.slug, state.language) + `#${encodeURIComponent(anchor)}`);
  }

  async function renderPreview() {
    if (!state.slug) return;
    document.getElementById("preview-status").textContent = "渲染中…";
    try {
      const data = await request("/SRD/api/preview", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: textarea.value, language: state.language }),
      });
      document.getElementById("preview").innerHTML = data.html;
      document.getElementById("preview-status").textContent = "与正式构建规则一致";
      if (state.pendingAnchor) {
        const anchor = state.pendingAnchor;
        state.pendingAnchor = "";
        requestAnimationFrame(() => scrollPreviewTo(anchor));
      }
    } catch (error) {
      document.getElementById("preview-status").textContent = `预览失败：${error.message}`;
    }
  }

  async function save() {
    if (!isDirty() || !currentPath()) return;
    const name = displayName.value.trim();
    saveSetting("dh-srd-editor-name", name);
    saveButton.disabled = true;
    setStatus("正在完整构建并发布…");
    try {
      const data = await request("/SRD/api/save", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: currentPath(), content: textarea.value, baseVersion: state.version, displayName: name }),
      });
      state.original = textarea.value;
      state.version = data.version;
      document.getElementById("document-version").textContent = `版本 ${data.version}`;
      setStatus(data.gitSync?.status === "pending" ? "已发布；GitHub 正在后台同步" : data.message);
      updateSaveState();
    } catch (error) {
      if (error.status === 409) showConflict(error.data);
      setStatus(`保存失败：${error.message}`, true);
      updateSaveState();
    }
  }

  function showConflict(data) {
    const panel = document.getElementById("conflict-panel");
    document.getElementById("server-content").value = data.currentContent || "";
    panel.dataset.version = data.currentVersion || "";
    panel.hidden = false;
  }

  function insertSage() {
    const label = state.language === "zh" ? "贤者恩泽：在此填写标题" : "SAGE-TOUCHED: Your title";
    const content = state.language === "zh" ? "在此填写补充说明" : "Add commentary here";
    const template = `\n<div class="sage-touched">\n<details>\n<summary>${label}</summary>\n\n${content}\n</details>\n</div>\n`;
    textarea.setRangeText(template, textarea.selectionStart, textarea.selectionEnd, "end");
    textarea.dispatchEvent(new Event("input"));
    textarea.focus();
  }

  document.getElementById("language-button").addEventListener("click", () => {
    const language = state.language === "zh" ? "en" : "zh";
    if (state.slug && canLeaveDocument()) loadDocument(state.slug, language);
  });
  textarea.addEventListener("input", () => { updateSaveState(); schedulePreview(); });
  saveButton.addEventListener("click", save);
  document.getElementById("sage-btn").addEventListener("click", insertSage);
  document.getElementById("menu-button").addEventListener("click", () => document.body.classList.add("sidebar-open"));
  document.getElementById("sidebar-close").addEventListener("click", () => document.body.classList.remove("sidebar-open"));
  document.getElementById("sidebar-backdrop").addEventListener("click", () => document.body.classList.remove("sidebar-open"));
  document.getElementById("accept-server").addEventListener("click", () => {
    state.original = document.getElementById("server-content").value;
    state.version = document.getElementById("conflict-panel").dataset.version;
    textarea.value = state.original;
    document.getElementById("conflict-panel").hidden = true;
    schedulePreview(); updateSaveState(); setStatus("已载入服务器版本");
  });
  window.addEventListener("beforeunload", (event) => { if (isDirty()) { event.preventDefault(); event.returnValue = ""; } });
  displayName.value = readSetting("dh-srd-editor-name", "");
  loadPages();
})();
