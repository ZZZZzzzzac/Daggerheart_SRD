/* ── 配置 ── */
const REPO = 'ZZZZzzzzac/Daggerheart_SRD';
const BRANCH = 'master';

/* ── 状态 ── */
let state = {
  pages: {},          // { slug: { zh: 'src/pages/.../zh.md', en: 'src/pages/.../en.md' } }
  currentSlug: null,
  currentLang: 'zh',
  originalContent: '',
  // token 优先级：localStorage > BUILTIN_TOKEN（在 config.token.js 中设置，不入 git）
  token: localStorage.getItem('gh_token') || (typeof BUILTIN_TOKEN !== 'undefined' ? BUILTIN_TOKEN : null),
};

let editor = null;    // CodeMirror 实例

/* ── 页面列表 ── */
async function loadPageList() {
  try {
    const resp = await fetch(`https://api.github.com/repos/${REPO}/git/trees/${BRANCH}?recursive=1`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const tree = await resp.json();

    for (const item of tree.tree) {
      if (!item.path.startsWith('src/pages/') || !item.path.endsWith('.md')) continue;
      const parts = item.path.replace('src/pages/', '').split('/');
      const lang = parts.pop().replace('.md', '');
      const slug = parts.join('/');

      if (!state.pages[slug]) state.pages[slug] = {};
      state.pages[slug][lang] = item.path;
    }

    populateSelect();
  } catch (e) {
    setStatus('加载页面列表失败: ' + e.message, true);
  }
}

function populateSelect() {
  const sel = document.getElementById('page-select');
  const slugs = Object.keys(state.pages).sort();

  // 按顶级目录分组
  const groups = {};
  for (const slug of slugs) {
    const top = slug.split('/')[0];
    if (!groups[top]) groups[top] = [];
    groups[top].push(slug);
  }

  for (const [group, items] of Object.entries(groups)) {
    const optgroup = document.createElement('optgroup');
    optgroup.label = getPageTitle(group);
    for (const slug of items) {
      const opt = document.createElement('option');
      opt.value = slug;
      const displayName = slug.includes('/')
        ? slug.split('/').slice(1).join(' / ')
        : getPageTitle(slug);
      opt.textContent = displayName;
      optgroup.appendChild(opt);
    }
    sel.appendChild(optgroup);
  }
}

/* ── 页面标题映射 ── */
const PAGE_TITLES = {
  'introduction': '介绍 Introduction',
  'character-creation': '创建角色 Character Creation',
  'core-resources/domains': '领域 Domains',
  'core-resources/classes': '职业 Classes',
  'core-resources/ancestries': '种族 Ancestries',
  'core-resources/communities': '社群 Communities',
  'core-mechanics': '核心机制 Core Mechanics',
  'core-mechanics/equipment': '装备表格 Equipment Tables',
  'core-mechanics/combat-wheelchair': '战斗轮椅 Combat Wheelchair',
  'running-a-game': '运作一场游戏 Running a Game',
  'adversaries-and-environments/adversary-mechanics': '敌人机制 Adversary Mechanics',
  'adversaries-and-environments/adversary-data': '敌人数据 Adversary Data',
  'adversaries-and-environments/environment-mechanics': '环境机制 Environment Mechanics',
  'adversaries-and-environments/environment-data': '环境数据 Environment Data',
  'campaign-frames': '战役框架 Campaign Frames',
  'appendix/domain-cards': '领域卡 Domain Cards',
};

function getPageTitle(slug) {
  return PAGE_TITLES[slug] || slug;
}

/* ── 加载文件 ── */
async function loadFile(slug, lang) {
  const path = state.pages[slug]?.[lang];
  if (!path) {
    setStatus(`文件不存在: ${slug}/${lang}`, true);
    return;
  }

  state.currentSlug = slug;
  state.currentLang = lang;
  setStatus('加载中...');

  // 先试 GitHub API，失败后 fallback 到 raw CDN
  let content = null;
  const apis = [
    async () => {
      const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${path}`);
      if (!r.ok) throw new Error(`GitHub API HTTP ${r.status}`);
      const d = await r.json();
      const raw = atob(d.content.replace(/\n/g, ''));
      return decodeURIComponent(escape(raw));
    },
    async () => {
      const r = await fetch(`https://raw.githubusercontent.com/${REPO}/${BRANCH}/${path}`);
      if (!r.ok) throw new Error(`raw CDN HTTP ${r.status}`);
      return await r.text();
    },
  ];

  for (const api of apis) {
    try {
      content = await api();
      break;
    } catch (e) {
      console.warn('fetch failed, trying next:', e.message);
    }
  }

  if (content === null) {
    setStatus(`加载失败: 无法获取 ${slug}/${lang}.md（两种方式都失败了）`, true);
    return;
  }

  state.originalContent = content;
  editor.setValue(content);
  editor.clearHistory();
  setStatus('已加载: ' + slug + '/' + lang + '.md');
  updatePreview();
  updateSaveBtn();
}

/* ── 预览 ── */
function updatePreview() {
  const content = editor ? editor.getValue() : '';
  const html = marked.parse(content, { breaks: true });
  document.getElementById('preview').innerHTML = html;
}

/* ── CodeMirror ── */
function setupEditor() {
  const textarea = document.getElementById('editor-textarea');
  editor = CodeMirror.fromTextArea(textarea, {
    mode: 'markdown',
    lineNumbers: true,
    lineWrapping: true,
    inputStyle: 'textarea',
    extraKeys: {
      'Enter': 'newlineAndIndentContinueMarkdownList',
    },
  });

  editor.on('change', () => {
    updatePreview();
    updateSaveBtn();
  });

  setupScrollSync();
}

/* ── UI 更新 ── */
function setStatus(msg, isError) {
  const el = document.getElementById('save-status');
  if (el) {
    el.textContent = msg;
    el.style.color = isError ? '#c00' : '#666';
  }
}

function updateSaveBtn() {
  const btn = document.getElementById('save-btn');
  const modified = editor && editor.getValue() !== state.originalContent;
  btn.disabled = !modified || !state.token;
  if (!state.token) {
    btn.title = '请先设置 GitHub Token';
  } else if (!modified) {
    btn.title = '内容未修改';
  } else {
    btn.title = '';
  }
}

/* ── 滚动同步 ── */
let scrollSource = null;  // 避免循环同步

function setupScrollSync() {
  const preview = document.getElementById('preview');

  // CodeMirror 滚动 → 同步预览
  editor.on('scroll', () => {
    if (scrollSource === 'preview') return;
    scrollSource = 'editor';
    const info = editor.getScrollInfo();
    const pct = info.height > info.clientHeight
      ? info.top / (info.height - info.clientHeight)
      : 0;
    preview.scrollTop = pct * (preview.scrollHeight - preview.clientHeight);
    setTimeout(() => { scrollSource = null; }, 50);
  });

  // 预览滚动 → 同步编辑器
  preview.addEventListener('scroll', () => {
    if (scrollSource === 'editor') return;
    scrollSource = 'preview';
    const pct = preview.scrollHeight > preview.clientHeight
      ? preview.scrollTop / (preview.scrollHeight - preview.clientHeight)
      : 0;
    const info = editor.getScrollInfo();
    editor.scrollTo(null, pct * (info.height - info.clientHeight));
    setTimeout(() => { scrollSource = null; }, 50);
  });
}

/* ── Token ── */
function openTokenModal() {
  document.getElementById('token-input').value = state.token || '';
  $('#token-modal').modal('show');
}

function saveToken() {
  const token = document.getElementById('token-input').value.trim();
  state.token = token || null;
  if (token) {
    localStorage.setItem('gh_token', token);
  } else {
    localStorage.removeItem('gh_token');
  }
  $('#token-modal').modal('hide');
  updateSaveBtn();
  setStatus(token ? 'Token 已保存' : 'Token 已清除');
}

/* ── 提交 PR ── */
async function submitPR() {
  const slug = state.currentSlug;
  const lang = state.currentLang;
  const newContent = editor.getValue();
  const desc = document.getElementById('pr-description').value.trim() || `编辑 ${slug}/${lang}.md`;

  const path = state.pages[slug]?.[lang];
  if (!path || !newContent) return;

  const headers = {
    Authorization: `Bearer ${state.token}`,
    'Content-Type': 'application/json',
  };

  const PR_BASE = `https://api.github.com/repos/${REPO}`;
  const branchName = `edit-${slug.replace(/\//g, '-')}-${Date.now()}`;
  const progressBar = document.getElementById('pr-progress-bar');
  const progressDiv = document.getElementById('pr-progress');
  const resultDiv = document.getElementById('pr-result');

  function setProgress(pct, msg) {
    progressDiv.style.display = 'block';
    progressBar.style.width = pct + '%';
    progressBar.textContent = msg || '';
  }

  try {
    setProgress(5, '获取最新提交...');

    // 1. 获取 master 最新 commit SHA
    const refResp = await fetch(`${PR_BASE}/git/refs/heads/${BRANCH}`, { headers });
    if (!refResp.ok) throw new Error('获取 ref 失败: ' + (await refResp.text()));
    const refData = await refResp.json();
    const masterSha = refData.object.sha;

    setProgress(20, '创建分支...');

    // 2. 创建新分支
    const branchResp = await fetch(`${PR_BASE}/git/refs`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ref: `refs/heads/${branchName}`, sha: masterSha }),
    });
    if (!branchResp.ok) throw new Error('创建分支失败: ' + (await branchResp.text()));

    setProgress(35, '提交内容...');

    // 3. 创建 blob（新文件内容）
    const blobResp = await fetch(`${PR_BASE}/git/blobs`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ content: newContent, encoding: 'utf-8' }),
    });
    if (!blobResp.ok) throw new Error('创建 blob 失败: ' + (await blobResp.text()));
    const blobData = await blobResp.json();

    // 4. 获取当前 master 的 tree SHA
    const masterCommitResp = await fetch(`${PR_BASE}/git/commits/${masterSha}`, { headers });
    if (!masterCommitResp.ok) throw new Error('获取 commit 失败');
    const masterCommit = await masterCommitResp.json();

    // 5. 创建新 tree
    const treeResp = await fetch(`${PR_BASE}/git/trees`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        base_tree: masterCommit.tree.sha,
        tree: [{ path, mode: '100644', type: 'blob', sha: blobData.sha }],
      }),
    });
    if (!treeResp.ok) throw new Error('创建 tree 失败: ' + (await treeResp.text()));
    const treeData = await treeResp.json();

    // 6. 创建 commit
    const commitResp = await fetch(`${PR_BASE}/git/commits`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message: `编辑: ${path}`,
        tree: treeData.sha,
        parents: [masterSha],
      }),
    });
    if (!commitResp.ok) throw new Error('创建 commit 失败: ' + (await commitResp.text()));
    const commitData = await commitResp.json();

    setProgress(65, '更新分支引用...');

    // 7. 将新分支指向新 commit
    await fetch(`${PR_BASE}/git/refs/heads/${branchName}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({ sha: commitData.sha, force: true }),
    });

    setProgress(80, '创建 PR...');

    // 8. 创建 PR
    const prResp = await fetch(`${PR_BASE}/pulls`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        title: `编辑: ${path}`,
        head: branchName,
        base: BRANCH,
        body: desc,
      }),
    });
    if (!prResp.ok) throw new Error('创建 PR 失败: ' + (await prResp.text()));
    const prData = await prResp.json();

    setProgress(100, '完成！');
    resultDiv.innerHTML = `<p>PR 已创建：<a href="${prData.html_url}" target="_blank">${prData.html_url}</a></p>`;
    state.originalContent = newContent;
    updateSaveBtn();
  } catch (e) {
    setProgress(0, '');
    resultDiv.innerHTML = `<p class="text-danger">错误: ${e.message}</p>`;
  }
}

/* ── 事件绑定 ── */
document.addEventListener('DOMContentLoaded', () => {
  setupEditor();
  loadPageList();

  // 页面选择
  document.getElementById('page-select').addEventListener('change', (e) => {
    const slug = e.target.value;
    if (slug) loadFile(slug, state.currentLang);
  });

  // 语言切换
  document.getElementById('lang-zh-btn').addEventListener('click', (e) => {
    e.preventDefault();
    if (state.currentSlug && state.currentLang !== 'zh') {
      state.currentLang = 'zh';
      document.getElementById('lang-zh-btn').className = 'lang-active';
      document.getElementById('lang-en-btn').className = 'lang-inactive';
      loadFile(state.currentSlug, 'zh');
    }
  });
  document.getElementById('lang-en-btn').addEventListener('click', (e) => {
    e.preventDefault();
    if (state.currentSlug && state.currentLang !== 'en') {
      state.currentLang = 'en';
      document.getElementById('lang-en-btn').className = 'lang-active';
      document.getElementById('lang-zh-btn').className = 'lang-inactive';
      loadFile(state.currentSlug, 'en');
    }
  });

  // Token
  document.getElementById('token-btn').addEventListener('click', (e) => {
    e.preventDefault();
    openTokenModal();
  });
  document.getElementById('token-save-btn').addEventListener('click', saveToken);

  // PR
  document.getElementById('save-btn').addEventListener('click', () => {
    if (!state.token) {
      openTokenModal();
      return;
    }
    document.getElementById('pr-result').innerHTML = '';
    document.getElementById('pr-result').style.display = 'none';
    document.getElementById('pr-progress').style.display = 'none';
    document.getElementById('pr-description').value = '';
    $('#pr-modal').modal('show');
  });
  document.getElementById('pr-submit-btn').addEventListener('click', submitPR);
});
