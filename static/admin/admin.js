(function () {
  "use strict";
  const list = document.getElementById("feedback-list");
  const statusText = document.getElementById("admin-status");
  let currentStatus = "";

  async function request(url, options) {
    const response = await fetch(url, { credentials: "same-origin", ...options });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
  }

  function pageUrl(item) {
    const base = `${location.origin}/SRD/`;
    return `${base}${item.page_path ? `${item.page_path}/` : ""}#${encodeURIComponent(item.anchor || "top")}`;
  }

  function render(items) {
    list.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("p"); empty.className = "empty-inbox"; empty.textContent = "这个分类里没有反馈"; list.append(empty); return;
    }
    items.forEach((item) => {
      const card = document.getElementById("feedback-template").content.firstElementChild.cloneNode(true);
      card.dataset.id = item.id;
      card.classList.toggle("unread", !item.is_read);
      card.querySelector(".feedback-id").textContent = `#${item.id} · ${labelFor(item.status)}`;
      card.querySelector("time").textContent = new Date(item.created_at).toLocaleString();
      const location = card.querySelector(".feedback-location");
      location.textContent = `${item.page_path || "首页"} #${item.anchor}`;
      location.href = pageUrl(item);
      card.querySelector(".feedback-message").textContent = item.message;
      const contact = card.querySelector(".feedback-contact");
      contact.textContent = item.contact ? `联系方式：${item.contact}` : "未留联系方式";
      card.querySelector("select").value = item.status;
      card.querySelector("textarea").value = item.internal_note || "";
      card.querySelector(".save-feedback").addEventListener("click", () => saveCard(card));
      list.append(card);
    });
  }

  function labelFor(status) { return ({pending: "待处理", in_progress: "处理中", accepted: "已采纳", closed: "已关闭"})[status] || status; }

  async function load() {
    statusText.textContent = "正在读取反馈…";
    try {
      const syncData = await request("/SRD/api/admin/publish-status");
      const sync = syncData.gitSync || {};
      const syncStatus = document.getElementById("git-sync-status");
      syncStatus.classList.toggle("error", sync.status === "pending" && Boolean(sync.error));
      syncStatus.textContent = sync.status === "synced" ? "GitHub 备份已同步" : sync.status === "pending" ? `GitHub 备份待同步${sync.error ? `：${sync.error}` : ""}` : "尚无待同步发布";
      const query = currentStatus ? `?status=${currentStatus}` : "";
      const data = await request(`/SRD/api/admin/feedback${query}`);
      document.getElementById("unread-count").textContent = data.unread ? `${data.unread} 条未读` : "";
      statusText.textContent = `${data.feedback.length} 条反馈`;
      render(data.feedback);
    } catch (error) { statusText.textContent = `加载失败：${error.message}`; }
  }

  async function saveCard(card) {
    const button = card.querySelector(".save-feedback"); button.disabled = true; button.textContent = "保存中…";
    try {
      await request("/SRD/api/admin/feedback/update", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({id: Number(card.dataset.id), status: card.querySelector("select").value, note: card.querySelector("textarea").value}) });
      button.textContent = "已保存"; card.classList.remove("unread"); setTimeout(() => { button.textContent = "保存处理结果"; button.disabled = false; }, 800);
    } catch (error) { button.textContent = error.message; button.disabled = false; }
  }

  document.getElementById("status-tabs").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-status]"); if (!button) return;
    currentStatus = button.dataset.status; document.querySelectorAll("#status-tabs button").forEach((item) => item.classList.toggle("active", item === button)); load();
  });
  document.getElementById("refresh-button").addEventListener("click", load);
  load();
})();
