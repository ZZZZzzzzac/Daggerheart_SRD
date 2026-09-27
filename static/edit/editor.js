(function () {
  "use strict";

  const state = {
    pages: {},
    site: null,
    slug: "",
    language: readSetting("dh-srd-lang", "zh") === "en" ? "en" : "zh",
    documents: new Map(),
    previewTimer: null,
    previewSequence: 0,
    previewFallbackTimer: null,
    loadSequence: 0,
    pendingAnchor: "",
    syncTimer: null,
    glossaryEditor: null,
  };
  const textarea = document.getElementById("editor-textarea");
  const status = document.getElementById("save-status");
  const saveButton = document.getElementById("save-btn");
  const publishDialog = document.getElementById("publish-dialog");
  const publishForm = document.getElementById("publish-form");
  const publishName = document.getElementById("publish-name");
  const previewWorker = new Worker("preview-worker.mjs?v=20260927-domain-cards", { type: "module" });

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

  function documentFor(slug = state.slug, language = state.language) {
    if (state.pages[slug]?.kind === "glossary") language = "zh";
    const path = state.pages[slug]?.files?.[language];
    return path ? state.documents.get(path) : undefined;
  }

  function dirtyDocuments() {
    return [...state.documents.values()].filter((draft) => draft.content !== draft.original);
  }

  function updateSaveState() {
    const count = dirtyDocuments().length;
    document.getElementById("pending-count").textContent = `待发布 ${count} 项`;
    saveButton.disabled = count === 0;
  }
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

  function slugIsDirty(slug) {
    return ["zh", "en"].some((language) => {
      const draft = documentFor(slug, language);
      return draft && draft.content !== draft.original;
    });
  }

  function navigate(event, path, language = state.language, anchor = "") {
    event.preventDefault();
    event.stopPropagation();
    loadDocument(path, language, anchor);
  }

  function summaryRow(title, path) {
    const row = node("span", "tree-summary-row");
    row.append(node("span", "tree-caret", "›"));
    const link = node("a", "tree-page-link", title);
    link.href = editorUrl(path);
    link.addEventListener("click", (event) => navigate(event, path));
    row.append(link);
    return row;
  }

  function buildPageBranch(page) {
    const details = node("details", `tree-page${page.path === state.slug ? " current" : ""}${slugIsDirty(page.path) ? " dirty" : ""}`);
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
        link.addEventListener("click", (event) => navigate(event, page.path, state.language, heading.anchor));
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
    if (state.pages.glossary) {
      const glossaryItem = node("li");
      glossaryItem.append(buildPageBranch(state.pages.glossary));
      list.append(glossaryItem);
    }
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
    const glossary = page?.kind === "glossary";
    document.getElementById("language-button").hidden = glossary;
    document.getElementById("sage-btn").hidden = glossary;
    document.getElementById("glossary-form").hidden = !glossary;
    const title = textFor(page?.title) || state.slug;
    document.getElementById("editor-document-label").textContent = title;
    document.title = `${title} · SRD 编辑器`;
    document.querySelector(".editor-shell").dataset.pagePath = state.slug;
    document.getElementById("language-button").textContent = state.language === "zh" ? "中文" : "EN";
    document.documentElement.lang = state.language === "zh" ? "zh-CN" : "en";
    const url = glossary ? "../" : readerUrl(state.slug);
    document.getElementById("reader-link").href = url;
    document.getElementById("sidebar-reader-link").href = url;
    history.replaceState(null, "", editorUrl(state.slug, state.language) + (state.pendingAnchor ? `#${encodeURIComponent(state.pendingAnchor)}` : ""));
    renderTree();
  }

  async function loadDocument(slug, language, anchor = "") {
    if (state.pages[slug]?.kind === "glossary") language = "zh";
    if (!state.pages[slug]?.files?.[language]) { setStatus("该语言文件不存在", true); return; }
    const sequence = ++state.loadSequence;
    setStatus("加载中…");
    try {
      const files = state.pages[slug].files;
      const missing = ["zh", "en"].filter((item) => files[item] && !state.documents.has(files[item]));
      const loaded = await Promise.all(missing.map(async (item) => {
        const path = files[item];
        const data = await request(`/SRD/api/get-file?path=${encodeURIComponent(path)}`);
        return { path, slug, language: item, content: data.content, original: data.content, version: data.version };
      }));
      loaded.forEach((draft) => state.documents.set(draft.path, draft));
      if (sequence !== state.loadSequence) return;
      state.slug = slug;
      state.language = language;
      state.pendingAnchor = anchor;
      const draft = documentFor();
      textarea.value = draft.content;
      textarea.disabled = false;
      document.getElementById("document-version").textContent = `版本 ${draft.version}`;
      document.getElementById("conflict-panel").hidden = true;
      saveSetting("dh-srd-lang", language);
      updatePageChrome();
      updateSaveState();
      renderPreview();
      await showGlossaryForm(state.pages[slug].kind === "glossary");
      setStatus("已载入；未发布修改保存在当前浏览器会话");
      document.body.classList.remove("sidebar-open");
    } catch (error) { setStatus(`加载失败：${error.message}`, true); }
  }

  function schedulePreview() {
    clearTimeout(state.previewTimer);
    state.previewTimer = setTimeout(renderPreview, 160);
    document.getElementById("preview-status").textContent = "等待更新";
  }

  function scrollPreviewTo(anchor) {
    const heading = [...document.querySelectorAll("#preview [data-anchor]")].find((item) => item.dataset.anchor === anchor);
    heading?.scrollIntoView({ block: "start" });
    if (anchor) history.replaceState(null, "", editorUrl(state.slug, state.language) + `#${encodeURIComponent(anchor)}`);
  }

  function renderPreview() {
    if (!state.slug) return;
    if (state.slug === "glossary") {
      const sequence = ++state.previewSequence;
      clearTimeout(state.previewFallbackTimer);
      const content = documentFor().content;
      import("../js/glossary-core.mjs?v=20260927-trim").then(({ parseGlossary }) => {
        if (sequence !== state.previewSequence) return;
        try {
          const { terms } = parseGlossary(content);
          const preview = document.getElementById("preview");
          preview.replaceChildren(node("h2", "", "术语表预览"), node("p", "", `${terms.length} 条术语`));
          for (const term of terms) {
            const entry = node("details", "glossary-preview-entry");
            entry.append(node("summary", "", `${term.zh}`));
            entry.append(node("p", "", term.description));
            preview.append(entry);
          }
          document.getElementById("preview-status").textContent = "Markdown 格式有效";
        } catch (error) { document.getElementById("preview-status").textContent = `格式错误：${error.message}`; }
      });
      return;
    }
    const zh = documentFor(state.slug, "zh");
    const en = documentFor(state.slug, "en");
    if (!zh || !en) return;
    const sequence = ++state.previewSequence;
    document.getElementById("preview-status").textContent = "本地渲染中…";
    previewWorker.postMessage({ id: sequence, sequence, zh: zh.content, en: en.content, language: state.language, pagePath: state.slug });
    clearTimeout(state.previewFallbackTimer);
    state.previewFallbackTimer = setTimeout(async () => {
      if (sequence !== state.previewSequence) return;
      try {
        const { renderPair } = await import("../js/render-core.mjs?v=20260927-domain-cards");
        applyPreviewResult(sequence, renderPair(zh.content, en.content, { pagePath: state.slug }).html[state.language]);
      } catch (error) {
        document.getElementById("preview-status").textContent = `预览失败：${error.message}`;
      }
    }, 1200);
  }

  function applyPreviewResult(sequence, html) {
    if (sequence !== state.previewSequence) return;
    clearTimeout(state.previewFallbackTimer);
    document.getElementById("preview").innerHTML = html;
    document.getElementById("preview-status").textContent = "本地预览 · 与正式构建同源";
    if (state.pendingAnchor) {
      const anchor = state.pendingAnchor;
      state.pendingAnchor = "";
      requestAnimationFrame(() => scrollPreviewTo(anchor));
    }
  }

  previewWorker.addEventListener("message", (event) => {
    const responseSequence = event.data.sequence ?? event.data.id;
    if (responseSequence !== state.previewSequence) return;
    if (event.data.error) {
      document.getElementById("preview-status").textContent = `预览失败：${event.data.error}`;
      return;
    }
    applyPreviewResult(responseSequence, event.data.html);
  });

  previewWorker.addEventListener("error", (event) => {
    document.getElementById("preview-status").textContent = `预览失败：${event.message}`;
  });

  function pageLabel(draft) {
    const page = state.pages[draft.slug];
    if (page?.kind === "glossary") return "术语表 · 中英共用";
    const title = page?.title?.[draft.language] || page?.title?.zh || draft.slug;
    return `${title} · ${draft.language === "zh" ? "中文" : "EN"}`;
  }

  function openPublishDialog() {
    const dirty = dirtyDocuments();
    if (!dirty.length) return;
    const list = document.getElementById("publish-list");
    list.replaceChildren(...dirty.map((draft) => node("li", "", pageLabel(draft))));
    document.getElementById("publish-error").textContent = "";
    publishName.value = readSetting("dh-srd-editor-name", "");
    publishDialog.showModal();
    publishName.focus();
  }

  function closePublishDialog() {
    if (!publishForm.dataset.busy) publishDialog.close();
  }

  async function pollGitSync() {
    clearTimeout(state.syncTimer);
    try {
      const data = await request("/SRD/api/publish-status");
      const sync = data.gitSync || data;
      if (sync.status === "synced") { setStatus("已同步至 GitHub"); return; }
      if (sync.status === "failed") {
        setStatus(`站点已发布；GitHub 同步失败：${sync.error || "未知错误"}`, true);
        return;
      }
      setStatus(sync.status === "retrying"
        ? `站点已发布；GitHub 同步正在重试：${sync.error || "网络异常"}`
        : "已发布；GitHub 正在后台同步", sync.status === "retrying");
      state.syncTimer = setTimeout(pollGitSync, 2000);
    } catch (error) {
      setStatus(`站点已发布；同步状态读取失败：${error.message}`, true);
      state.syncTimer = setTimeout(pollGitSync, 5000);
    }
  }

  async function publish(event) {
    event.preventDefault();
    const name = publishName.value.trim();
    const dirty = dirtyDocuments();
    if (!name) {
      document.getElementById("publish-error").textContent = "请输入编辑者名称";
      publishName.focus();
      return;
    }
    if (!dirty.length) { publishDialog.close(); return; }
    publishForm.dataset.busy = "true";
    [...publishForm.elements].forEach((element) => { element.disabled = true; });
    document.getElementById("publish-error").textContent = "正在完整构建并发布…";
    setStatus("正在完整构建并发布…");
    try {
      const data = await request("/SRD/api/save", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          displayName: name,
          changes: dirty.map((draft) => ({
            path: draft.path,
            content: draft.content,
            baseVersion: draft.version,
          })),
        }),
      });
      dirty.forEach((draft) => {
        draft.original = draft.content;
        draft.version = data.versions?.[draft.path] || draft.version;
      });
      saveSetting("dh-srd-editor-name", name);
      publishDialog.close();
      const current = documentFor();
      if (current) document.getElementById("document-version").textContent = `版本 ${current.version}`;
      renderTree();
      updateSaveState();
      if (data.gitSync?.status === "synced") setStatus("已同步至 GitHub");
      else {
        setStatus("已发布；GitHub 正在后台同步");
        pollGitSync();
      }
    } catch (error) {
      if (error.status === 409) await showConflict(error.data);
      document.getElementById("publish-error").textContent = `发布失败：${error.message}`;
      setStatus(`发布失败：${error.message}`, true);
    } finally {
      delete publishForm.dataset.busy;
      [...publishForm.elements].forEach((element) => { element.disabled = false; });
      updateSaveState();
    }
  }

  async function showConflict(data) {
    const conflict = data.conflicts?.[0] || data;
    const draft = conflict.path ? state.documents.get(conflict.path) : documentFor();
    if (draft && (draft.slug !== state.slug || draft.language !== state.language)) {
      await loadDocument(draft.slug, draft.language);
    }
    const panel = document.getElementById("conflict-panel");
    document.getElementById("server-content").value = conflict.currentContent || "";
    panel.dataset.path = conflict.path || draft?.path || "";
    panel.dataset.version = conflict.currentVersion || "";
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
    if (state.slug) loadDocument(state.slug, language);
  });
  textarea.addEventListener("input", () => {
    const draft = documentFor();
    if (!draft) return;
    draft.content = textarea.value;
    updateSaveState();
    renderTree();
    schedulePreview();
  });
  saveButton.addEventListener("click", openPublishDialog);
  publishForm.addEventListener("submit", publish);
  document.getElementById("publish-close").addEventListener("click", closePublishDialog);
  document.getElementById("publish-cancel").addEventListener("click", closePublishDialog);
  document.getElementById("sage-btn").addEventListener("click", insertSage);
  document.getElementById("menu-button").addEventListener("click", () => document.body.classList.add("sidebar-open"));
  document.getElementById("sidebar-close").addEventListener("click", () => document.body.classList.remove("sidebar-open"));
  document.getElementById("sidebar-backdrop").addEventListener("click", () => document.body.classList.remove("sidebar-open"));
  document.getElementById("accept-server").addEventListener("click", () => {
    const panel = document.getElementById("conflict-panel");
    const draft = state.documents.get(panel.dataset.path) || documentFor();
    if (!draft) return;
    draft.content = document.getElementById("server-content").value;
    draft.original = draft.content;
    draft.version = panel.dataset.version;
    if (draft === documentFor()) {
      textarea.value = draft.content;
      document.getElementById("document-version").textContent = `版本 ${draft.version}`;
      schedulePreview();
      if (draft.slug === "glossary") state.glossaryEditor?.load(draft.content);
    }
    panel.hidden = true;
    renderTree();
    updateSaveState();
    setStatus("已载入服务器版本");
  });
  async function showGlossaryForm(show) {
    const container = document.getElementById("glossary-editor");
    if (show && !state.glossaryEditor) {
      const { createGlossaryEditor } = await import("./glossary-editor.mjs?v=20260927-trim");
      if (state.slug !== "glossary") return;
      state.glossaryEditor = createGlossaryEditor(container, {
        onChange(content) {
          const draft = documentFor("glossary");
          if (!draft) return;
          draft.content = content; textarea.value = content;
          updateSaveState(); renderTree(); schedulePreview();
        },
      });
      container.querySelector("#glossary-markdown").addEventListener("click", () => showGlossaryForm(false));
    }
    if (show) state.glossaryEditor.load(documentFor("glossary").content);
    container.hidden = !show;
    document.querySelector(".editor-workspace").hidden = show;
  }
  document.getElementById("glossary-form").addEventListener("click", () => showGlossaryForm(true));
  window.addEventListener("beforeunload", (event) => {
    if (dirtyDocuments().length) { event.preventDefault(); event.returnValue = ""; }
  });
  loadPages();
})();
