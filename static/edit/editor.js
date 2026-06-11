/* ── 状态 ── */
let state = {
  pages: {},          // { slug: { zh: 'src/pages/.../zh.md', en: 'src/pages/.../en.md' } }
  currentSlug: null,
  currentLang: 'zh',
  originalContent: '',
};

let editor = null;    // CodeMirror 实例

/* ── 页面列表 ── */
async function loadPageList() {
  try {
    const resp = await fetch('/SRD/api/page-list');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    for (const path of data.pages) {
      const parts = path.replace('src/pages/', '').split('/');
      const lang = parts.pop().replace('.md', '');
      const slug = parts.join('/');

      if (!state.pages[slug]) state.pages[slug] = {};
      state.pages[slug][lang] = path;
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

  try {
    const resp = await fetch(`/SRD/api/get-file?path=${encodeURIComponent(path)}`);
    if (!resp.ok) {
      const data = await resp.json();
      throw new Error(data.error || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    state.originalContent = data.content;
    editor.setValue(data.content);
    editor.clearHistory();
    setStatus('已加载: ' + slug + '/' + lang + '.md');
    updatePreview();
    updateSaveBtn();
  } catch (e) {
    setStatus(`加载失败: ${e.message}`, true);
  }
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
  btn.disabled = !modified;
  if (!modified) {
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

/* ── 贤者恩泽模板插入 ── */
function insertSageTemplate() {
  if (!editor) return;
  const isZh = state.currentLang === 'zh';
  const label = isZh ? '贤者恩泽' : 'SAGE-TOUCHED';
  const titlePlaceholder = isZh ? '在此填写标题' : 'Your Title Here';
  const contentPlaceholder = isZh
    ? '在此填写补充说明内容（支持 markdown 语法）'
    : 'Your commentary content here (markdown supported)';
  const template = `<div class="sage-touched">\n<details>\n<summary>${label}：${titlePlaceholder}</summary>\n\n${contentPlaceholder}\n</details>\n</div>`;

  const cursor = editor.getCursor();
  editor.replaceRange('\n' + template + '\n', cursor);
  const titleStart = cursor.line + 3;
  const titleCol = label.length + 2;
  editor.setCursor({ line: titleStart, ch: titleCol });
  editor.focus();
}

/* ── 保存 ── */
async function saveDirect() {
  const slug = state.currentSlug;
  const lang = state.currentLang;
  const newContent = editor.getValue();
  const path = state.pages[slug]?.[lang];

  if (!path || !newContent) return;
  if (newContent === state.originalContent) return;

  setStatus('保存中...');
  document.getElementById('save-btn').disabled = true;

  try {
    const resp = await fetch('/SRD/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content: newContent }),
    });

    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || `服务器错误 (${resp.status})`);

    state.originalContent = newContent;
    updateSaveBtn();
    setStatus('✓ ' + (data.message || '保存成功'));
  } catch (e) {
    setStatus('保存失败: ' + e.message, true);
    document.getElementById('save-btn').disabled = false;
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

  // 保存
  document.getElementById('save-btn').addEventListener('click', saveDirect);

  // 贤者恩泽模板插入
  document.getElementById('sage-btn').addEventListener('click', insertSageTemplate);
});
