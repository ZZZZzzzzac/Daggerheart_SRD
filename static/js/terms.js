(function () {
  "use strict";

  const links = [...document.querySelectorAll(".srd-language .term-link[data-term-quote]")];
  const controls = document.getElementById("term-preferences");
  const toggle = document.getElementById("term-toggle");
  if (!links.length || !controls || !toggle) return;

  let enabled = true;
  try { enabled = localStorage.getItem("dh-srd-term-hints") !== "off"; } catch (_) { /* optional storage */ }
  let active = null;
  let pinned = false;
  let hideTimer;
  let suppressFocus = false;

  function element(tag, className, text) {
    const result = document.createElement(tag);
    result.className = className;
    if (text) result.textContent = text;
    return result;
  }

  const popup = element("div", "term-popover");
  popup.id = "term-popover";
  popup.hidden = true;
  popup.setAttribute("role", "dialog");
  popup.setAttribute("aria-modal", "false");
  popup.setAttribute("aria-labelledby", "term-title");
  popup.setAttribute("aria-describedby", "term-quote");
  const label = element("p", "term-label");
  const title = element("h2", "term-title");
  title.id = "term-title";
  const translation = element("p", "term-translation");
  const quote = element("blockquote", "term-quote");
  quote.id = "term-quote";
  const actions = element("div", "term-actions");
  const ruleLink = element("a", "term-source");
  const closeButton = element("button", "term-close");
  closeButton.type = "button";
  actions.append(ruleLink, closeButton);
  popup.append(label, title, translation, quote, actions);
  document.body.append(popup);

  function close(restoreFocus = false) {
    clearTimeout(hideTimer);
    const previous = active;
    active = null;
    pinned = false;
    popup.hidden = true;
    previous?.setAttribute("aria-expanded", "false");
    if (restoreFocus && previous) {
      suppressFocus = true;
      previous.focus({ preventScroll: true });
      suppressFocus = false;
    }
  }

  function syncControls() {
    toggle.setAttribute("aria-pressed", String(enabled));
    toggle.querySelector(".lang-zh").textContent = `术语提示：${enabled ? "开" : "关"}`;
    toggle.querySelector(".lang-en").textContent = `Term hints: ${enabled ? "on" : "off"}`;
    links.forEach((link) => {
      if (enabled) {
        link.setAttribute("aria-haspopup", "dialog");
        link.setAttribute("aria-expanded", "false");
        link.setAttribute("aria-controls", popup.id);
      } else {
        ["aria-haspopup", "aria-expanded", "aria-controls"].forEach((name) => link.removeAttribute(name));
      }
    });
    controls.hidden = false;
  }

  function show(link, pin = false) {
    if (!enabled || !link.dataset.termQuote) return;
    clearTimeout(hideTimer);
    if (active && active !== link) close();
    active = link;
    pinned = pin;
    const english = document.documentElement.lang === "en";
    label.textContent = english ? "SRD text · Verbatim excerpt" : "本站译文 · 原文摘录";
    title.textContent = english ? link.dataset.termEn : link.dataset.termZh;
    translation.textContent = english ? link.dataset.termZh : link.dataset.termEn;
    translation.lang = english ? "zh-CN" : "en";
    quote.textContent = link.dataset.termQuote;
    ruleLink.textContent = english ? "Read the full rule →" : "查看完整规则 →";
    ruleLink.href = link.href;
    closeButton.textContent = english ? "Close" : "收起";
    popup.hidden = false;
    link.setAttribute("aria-expanded", "true");
    position();
  }

  function position() {
    if (!active) return;
    // Fixed positioning avoids clipping in tables and stays within small screens.
    const rect = active.getBoundingClientRect();
    const width = popup.offsetWidth;
    const height = popup.offsetHeight;
    const left = Math.max(12, Math.min(rect.left, window.innerWidth - width - 12));
    const below = rect.bottom + 8;
    const top = below + height <= window.innerHeight - 12 ? below : rect.top - height - 8;
    popup.style.left = `${left}px`;
    popup.style.top = `${Math.max(12, Math.min(top, window.innerHeight - height - 12))}px`;
  }

  function scheduleClose() {
    clearTimeout(hideTimer);
    if (!pinned) hideTimer = window.setTimeout(() => {
      if (!popup.contains(document.activeElement) && document.activeElement !== active) close();
    }, 180);
  }

  links.forEach((link) => {
    link.addEventListener("pointerenter", (event) => {
      if (event.pointerType === "mouse" && !pinned) show(link);
    });
    link.addEventListener("pointerleave", scheduleClose);
    link.addEventListener("focus", () => { if (!suppressFocus) show(link); });
    link.addEventListener("click", (event) => {
      if (!enabled || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      if (active === link && pinned) close();
      else show(link, true);
    });
    link.addEventListener("keydown", (event) => {
      if (event.key === "Tab" && !event.shiftKey && active === link) {
        event.preventDefault();
        pinned = true;
        ruleLink.focus();
      }
    });
  });

  popup.addEventListener("pointerenter", () => clearTimeout(hideTimer));
  popup.addEventListener("pointerleave", scheduleClose);
  popup.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    if (event.shiftKey && event.target === ruleLink) {
      event.preventDefault();
      close(true);
    } else if (!event.shiftKey && event.target === closeButton) {
      event.preventDefault();
      // Continue from the originating link in document order, without trapping Tab.
      const focusable = [...document.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]')]
        .filter((item) => !popup.contains(item) && item.tabIndex >= 0 && item.getClientRects().length);
      const next = focusable[focusable.indexOf(active) + 1];
      close(true);
      next?.focus();
    }
  });
  closeButton.addEventListener("click", () => close(true));
  ruleLink.addEventListener("click", () => close());
  toggle.addEventListener("click", () => {
    close();
    enabled = !enabled;
    try { localStorage.setItem("dh-srd-term-hints", enabled ? "on" : "off"); } catch (_) { /* optional storage */ }
    syncControls();
  });
  document.addEventListener("pointerdown", (event) => {
    if (active && !active.contains(event.target) && !popup.contains(event.target)) close();
  });
  document.addEventListener("focusin", (event) => {
    if (active && event.target !== active && !popup.contains(event.target)) close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && active) {
      event.preventDefault();
      close(popup.contains(document.activeElement));
    }
  });
  window.addEventListener("resize", position);
  window.addEventListener("scroll", (event) => {
    if (!active || popup.contains(event.target)) return;
    const rect = active.getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > window.innerHeight) close(popup.contains(document.activeElement));
    else position();
  }, true);
  new MutationObserver(() => close()).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  syncControls();
})();
