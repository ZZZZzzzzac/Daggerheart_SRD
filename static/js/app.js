(function () {
  "use strict";

  const body = document.body;
  const root = document.documentElement;
  const baseUrl = body.dataset.baseUrl || "/";
  const article = document.querySelector(".srd-article");
  const currentPath = article?.dataset.pagePath || "";
  const state = {
    language: readSetting("dh-srd-lang", "zh"),
    searchLanguage: "zh",
    site: null,
    search: null,
    activeAnchor: "top",
  };

  function readSetting(key, fallback) {
    try { return localStorage.getItem(key) || fallback; } catch (_) { return fallback; }
  }

  function saveSetting(key, value) {
    try { localStorage.setItem(key, value); } catch (_) { /* storage is optional */ }
  }

  function textFor(value, language = state.language) {
    return value?.[language] || value?.zh || value?.en || "";
  }

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function pageUrl(path, anchor) {
    const normalizedBase = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
    const suffix = path ? `${path}/` : "";
    return `${normalizedBase}${suffix}${anchor ? `#${encodeURIComponent(anchor)}` : ""}`;
  }

  function syncAnchorIds(language) {
    document.querySelectorAll(".srd-language [data-anchor]").forEach((heading) => {
      const container = heading.closest(".srd-language");
      const isActive = container?.classList.contains(`lang-${language}`);
      if (isActive) heading.id = heading.dataset.anchor;
      else heading.removeAttribute("id");
    });
  }

  function setLanguage(language, persist = true) {
    state.language = language === "en" ? "en" : "zh";
    body.classList.toggle("show-en", state.language === "en");
    body.classList.toggle("show-zh", state.language === "zh");
    root.lang = state.language === "zh" ? "zh-CN" : "en";
    syncAnchorIds(state.language);
    if (persist) saveSetting("dh-srd-lang", state.language);
    if (state.site) {
      renderTree();
      renderBreadcrumbs();
      renderSequence();
      observeHeadings();
    }
    const hash = decodeURIComponent(location.hash.slice(1));
    if (hash) requestAnimationFrame(() => document.getElementById(hash)?.scrollIntoView());
  }

  function setTheme(theme, persist = true) {
    root.dataset.theme = theme;
    if (persist) saveSetting("dh-srd-theme", theme);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = theme === "dark" ? "#1c1b19" : "#f4efe5";
  }

  function initialTheme() {
    const saved = readSetting("dh-srd-theme", "");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  async function loadJson(url) {
    const response = await fetch(url, { credentials: "same-origin" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function pageMap() {
    return new Map((state.site?.pages || []).map((page) => [page.path, page]));
  }

  function summaryRow(title, href) {
    const row = node("span", "tree-summary-row");
    row.append(node("span", "tree-caret", "›"));
    if (href) {
      const link = node("a", "tree-page-link", title);
      link.href = href;
      link.addEventListener("click", (event) => event.stopPropagation());
      row.append(link);
    } else {
      row.append(node("span", "tree-title", title));
    }
    return row;
  }

  function buildPageBranch(page) {
    const details = node("details", `tree-page${page.path === currentPath ? " current" : ""}`);
    details.open = page.path === currentPath;
    const summary = node("summary");
    summary.append(summaryRow(textFor(page.title), pageUrl(page.path)));
    details.append(summary);
    const headings = page.headings?.[state.language] || [];
    if (headings.length) {
      const list = node("ul", "tree-headings");
      headings.forEach((heading) => {
        const item = node("li", `level-${heading.level}`);
        const link = node("a", "", heading.title);
        link.href = pageUrl(page.path, heading.anchor);
        link.dataset.anchor = heading.anchor;
        if (page.path === currentPath && heading.anchor === state.activeAnchor) link.classList.add("active");
        item.append(link);
        list.append(item);
      });
      details.append(list);
    }
    return details;
  }

  function renderTree() {
    const container = document.getElementById("contents-tree");
    if (!container || !state.site) return;
    container.replaceChildren();
    const pages = pageMap();
    const list = node("ul", "tree-list");
    state.site.tree.forEach((entry) => {
      const item = node("li");
      if (entry.type === "group") {
        const details = node("details", "tree-group");
        details.open = entry.children.includes(currentPath);
        const summary = node("summary");
        summary.append(summaryRow(textFor(entry.title)));
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

  function renderBreadcrumbs() {
    const container = document.getElementById("breadcrumbs");
    if (!container || !state.site) return;
    container.replaceChildren();
    const home = node("a", "", state.language === "zh" ? "首页" : "Home");
    home.href = pageUrl("");
    container.append(home);
    const page = pageMap().get(currentPath);
    if (!page) return;
    if (page.group) {
      container.append(node("span", "", "›"), node("b", "", textFor(page.group)));
    }
    container.append(node("span", "", "›"), node("b", "", textFor(page.title)));
  }

  function sequenceLink(page, direction) {
    const link = node("a", `sequence-link ${direction}`);
    link.href = pageUrl(page.path);
    const label = direction === "previous"
      ? (state.language === "zh" ? "← 上一页" : "← Previous")
      : (state.language === "zh" ? "下一页 →" : "Next →");
    link.append(node("small", "", label), node("b", "", textFor(page.title)));
    return link;
  }

  function renderSequence() {
    const container = document.getElementById("page-sequence");
    if (!container || !state.site) return;
    container.replaceChildren();
    const pages = pageMap();
    const current = pages.get(currentPath);
    if (!current) return;
    if (current.previous) container.append(sequenceLink(pages.get(current.previous), "previous"));
    else container.append(node("span"));
    if (current.next) container.append(sequenceLink(pages.get(current.next), "next"));
  }

  let observer = null;
  function observeHeadings() {
    if (observer) observer.disconnect();
    const visible = document.querySelector(`.srd-language.lang-${state.language}`);
    if (!visible || !("IntersectionObserver" in window)) return;
    const headings = [...visible.querySelectorAll("h1[id], h2[id], h3[id]")];
    observer = new IntersectionObserver((entries) => {
      const intersecting = entries.filter((entry) => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (!intersecting.length) return;
      state.activeAnchor = intersecting[0].target.dataset.anchor || intersecting[0].target.id;
      document.querySelectorAll(".tree-headings a").forEach((link) => link.classList.toggle("active", link.dataset.anchor === state.activeAnchor));
    }, { rootMargin: "-18% 0px -68% 0px", threshold: 0 });
    headings.forEach((heading) => observer.observe(heading));
  }

  function openDialog(id) {
    const dialog = document.getElementById(id);
    if (dialog && !dialog.open) dialog.showModal();
  }

  function closeDialog(id) {
    const dialog = document.getElementById(id);
    if (dialog?.open) dialog.close();
  }

  async function ensureSearchIndex() {
    if (!state.search) state.search = await loadJson(body.dataset.searchIndex);
    return state.search;
  }

  function snippetFor(bodyText, query) {
    const source = String(bodyText || "");
    const index = window.SrdSearch.normalize(source).indexOf(query);
    if (index < 0) return source.slice(0, 150) + (source.length > 150 ? "…" : "");
    const start = Math.max(0, index - 55);
    const end = Math.min(source.length, index + query.length + 95);
    return `${start ? "…" : ""}${source.slice(start, end)}${end < source.length ? "…" : ""}`;
  }

  async function runSearch() {
    const input = document.getElementById("search-input");
    const results = document.getElementById("search-results");
    const hint = document.getElementById("search-hint");
    const query = window.SrdSearch.normalize(input.value);
    results.replaceChildren();
    if (!query) {
      hint.textContent = state.searchLanguage === "zh" ? "输入文字后开始搜索" : "Type to search";
      return;
    }
    try {
      const index = await ensureSearchIndex();
      const matches = window.SrdSearch.search(index.records, query, state.searchLanguage, 50);
      hint.textContent = state.searchLanguage === "zh" ? `找到 ${matches.length} 个小节` : `${matches.length} sections found`;
      matches.forEach(({ record }) => {
        const item = node("li", "search-result");
        const link = node("a");
        link.href = pageUrl(record.path, record.anchor);
        link.addEventListener("click", () => closeDialog("search-dialog"));
        const meta = node("div", "search-result-meta");
        meta.append(node("span", "", record.pageTitle));
        link.append(meta, node("h3", "", record.heading), node("p", "", snippetFor(record.body, query)));
        item.append(link);
        results.append(item);
      });
    } catch (error) {
      hint.textContent = state.searchLanguage === "zh" ? "搜索资料加载失败" : "Search index failed to load";
    }
  }

  function currentFeedbackAnchor() {
    const headings = [...document.querySelectorAll(`.srd-language.lang-${state.language} h1[id], .srd-language.lang-${state.language} h2[id], .srd-language.lang-${state.language} h3[id]`)];
    let current = headings[0];
    headings.forEach((heading) => { if (heading.getBoundingClientRect().top < 180) current = heading; });
    return current?.dataset.anchor || current?.id || "top";
  }

  function openFeedback() {
    const page = pageMap().get(currentPath);
    const anchor = currentFeedbackAnchor();
    const context = document.getElementById("feedback-context");
    context.textContent = `${textFor(page?.title) || currentPath} · #${anchor}`;
    context.dataset.anchor = anchor;
    document.getElementById("feedback-status").textContent = "";
    openDialog("feedback-dialog");
  }

  async function submitFeedback(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const status = document.getElementById("feedback-status");
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    status.textContent = state.language === "zh" ? "正在提交…" : "Sending…";
    const payload = {
      message: document.getElementById("feedback-message").value,
      contact: document.getElementById("feedback-contact").value,
      website: document.getElementById("feedback-website").value,
      path: currentPath,
      anchor: document.getElementById("feedback-context").dataset.anchor || "top",
      language: state.language,
      version: state.site?.version || "unknown",
    };
    try {
      const response = await fetch(`${baseUrl}api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      form.reset();
      status.textContent = state.language === "zh" ? "反馈已进入收件箱" : "Feedback received";
      window.setTimeout(() => closeDialog("feedback-dialog"), 900);
    } catch (error) {
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }

  function bindEvents() {
    document.getElementById("language-button")?.addEventListener("click", () => setLanguage(state.language === "zh" ? "en" : "zh"));
    document.getElementById("theme-button")?.addEventListener("click", () => setTheme(root.dataset.theme === "dark" ? "light" : "dark"));
    document.getElementById("menu-button")?.addEventListener("click", () => body.classList.add("sidebar-open"));
    document.getElementById("sidebar-close")?.addEventListener("click", () => body.classList.remove("sidebar-open"));
    document.getElementById("sidebar-backdrop")?.addEventListener("click", () => body.classList.remove("sidebar-open"));
    document.getElementById("search-button")?.addEventListener("click", () => {
      state.searchLanguage = state.language;
      document.getElementById("search-language").textContent = state.searchLanguage === "zh" ? "中文" : "EN";
      openDialog("search-dialog");
      requestAnimationFrame(() => document.getElementById("search-input")?.focus());
    });
    document.getElementById("search-input")?.addEventListener("input", runSearch);
    document.getElementById("search-language")?.addEventListener("click", () => {
      state.searchLanguage = state.searchLanguage === "zh" ? "en" : "zh";
      document.getElementById("search-language").textContent = state.searchLanguage === "zh" ? "中文" : "EN";
      runSearch();
    });
    document.getElementById("feedback-button")?.addEventListener("click", openFeedback);
    document.getElementById("feedback-form")?.addEventListener("submit", submitFeedback);
    document.querySelectorAll("[data-close-dialog]").forEach((button) => button.addEventListener("click", () => closeDialog(button.dataset.closeDialog)));
    document.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        document.getElementById("search-button")?.click();
      }
    });
  }

  async function initialize() {
    setTheme(initialTheme(), false);
    setLanguage(state.language, false);
    bindEvents();
    try {
      state.site = await loadJson(body.dataset.siteIndex);
      renderTree();
      renderBreadcrumbs();
      renderSequence();
      observeHeadings();
    } catch (error) {
      const tree = document.getElementById("contents-tree");
      if (tree) tree.textContent = state.language === "zh" ? "目录加载失败" : "Contents failed to load";
    }
  }

  initialize();
})();
