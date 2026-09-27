import { environmentTypes } from './environment-core.mjs';
import { phraseMatches, highlightPhrase, clearHighlights } from './adversary-search.mjs';
const form = document.querySelector('#catalog-filters');
const results = document.querySelector('#adversary-results');
const cards = [...results.querySelectorAll('.adversary')];
const controls = Object.fromEntries(['query', 'tier', 'type', 'view'].map(key => [key, document.querySelector(`#adversary-${key}`)]));
const environment = document.querySelector('[data-catalog-kind]')?.dataset.catalogKind === 'environment';
const roles = environment ? environmentTypes : {bruiser: '斗士', horde: '集群', leader: '头目', minion: '杂兵', ranged: '远程', skulk: '潜伏', social: '社交', solo: '独狼', standard: '标准', support: '辅助'};
const defaults = {query: '', tier: '', type: '', view: 'full'};
let state = {...defaults};
const language = () => document.documentElement.lang === 'en' ? 'en' : 'zh';
const searchSelector = '.compact-name, .compact-role, .compact-stats, h3, h5, p, li, .stat-values > span, .stat-resources > span, .environment-difficulty';
const searchable = new Map(cards.map(card => [card, [...card.querySelectorAll(searchSelector)].filter(element => !element.parentElement.closest(searchSelector)).map(element => ({element, text: element.textContent}))]));

function readURL() {
  const params = new URLSearchParams(location.search);
  state = {...defaults};
  for (const key of Object.keys(state)) state[key] = params.get(key === 'query' ? 'q' : key) ?? defaults[key];
  state.tier = [...new Set(state.tier.split(',').filter(value => ['1', '2', '3', '4'].includes(value)))].sort().join(',');
  state.type = [...new Set(state.type.split(',').filter(value => Object.hasOwn(roles, value)))].sort().join(',');
  if (!['list', 'full'].includes(state.view)) state.view = 'full';
}

function writeURL() {
  const url = new URL(location.href);
  url.searchParams.delete('sort');
  for (const [key, value] of Object.entries(state)) {
    const param = key === 'query' ? 'q' : key;
    if (value !== defaults[key]) url.searchParams.set(param, value);
    else url.searchParams.delete(param);
  }
  history.replaceState(null, '', url);
}

function chips(key, values) {
  const selected = state[key].split(',');
  controls[key].closest('details').querySelector('.selection-count').textContent = state[key] ? ` (${selected.filter(Boolean).length})` : '';
  controls[key].replaceChildren(...values.map(([value, label]) => {
    const button = document.createElement('button');
    button.type = 'button'; button.dataset.value = value; button.textContent = label;
    button.setAttribute('aria-pressed', String(value ? selected.includes(value) : !state[key]));
    return button;
  }));
}

function localize() {
  const en = language() === 'en';
  controls.view.setAttribute('aria-label', en ? 'Compact view' : '紧凑视图');
  chips('tier', [['', en ? 'All tiers' : '全部位阶'], ...['1', '2', '3', '4'].map((n, i) => [n, `${en ? 'Tier' : '位阶'} ${n} · ${['1', '2–4', '5–7', '8–10'][i]} ${en ? 'level(s)' : '级'}`])]);
  chips('type', [['', en ? 'All types' : '全部类型'], ...Object.entries(roles).map(([key, zh]) => [key, en ? key[0].toUpperCase() + key.slice(1) : zh])]);
  controls.query.placeholder = en ? 'Search names, stats, features…' : '搜索名称、数值、特性…';
  controls.query.value = state.query;
}

function render() {
  closePreview();
  const en = language() === 'en';
  const query = state.query.trim();
  clearHighlights(results);
  let count = 0;
  for (const card of cards) {
    const matches = searchable.get(card).map(unit => ({...unit, hits: phraseMatches(unit.text, query)}));
    card.hidden = !!((state.tier && !state.tier.split(',').includes(card.dataset.tier)) || (state.type && !state.type.split(',').includes(card.dataset.type)) || (query && !matches.some(unit => unit.hits.length)));
    if (!card.hidden) {
      count++;
      for (const unit of matches) if (unit.hits.length) highlightPhrase(unit.element, unit.hits);
    }
    results.querySelector(`[data-tier-group="${card.dataset.tier}"] .adversary-grid`).append(card);
  }
  results.dataset.view = state.view;
  controls.view.setAttribute('aria-checked', String(state.view === 'list'));
  results.querySelectorAll('[data-tier-group]').forEach(group => {
    const visible = [...group.querySelectorAll('.adversary')].filter(card => !card.hidden).length;
    group.hidden = visible === 0;
    group.querySelector('.tier-count').textContent = visible;
  });
  document.querySelector('#catalog-count').textContent = en ? `${count} / ${cards.length} ${environment ? "environments" : "adversaries"}` : `${count} / ${cards.length} 个${environment ? "环境" : "敌人"}`;
  document.querySelector('#catalog-empty').hidden = count !== 0;
}

function openHash() {
  let id;
  try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
  const card = document.getElementById(id)?.closest('.adversary, .adversary-tier-group');
  if (!card) return;
  closePreview();
  if (card.hidden) {
    state = {...state, query: '', tier: '', type: ''};
    localize();
    render();
    writeURL();
  }
  state.view = 'full';
  controls.view.setAttribute('aria-checked', 'false');
  results.dataset.view = 'full';
  writeURL();
  requestAnimationFrame(() => card.scrollIntoView({block: 'start'}));
}

form.addEventListener('submit', event => event.preventDefault());
for (const [key, control] of Object.entries(controls).filter(([key]) => !['tier', 'type', 'view'].includes(key))) control.addEventListener(key === 'query' ? 'input' : 'change', () => {
  state[key] = control.value;
  // A new search should not leave an unrelated entry in the share URL.
  const url = new URL(location.href);
  url.hash = '';
  history.replaceState(null, '', url);
  writeURL();
  render(key === 'view');
});
function changeView(value) {
  state.view = value;
  history.replaceState(null, '', location.pathname + location.search);
  writeURL(); render();
}
controls.view.addEventListener('click', () => changeView(state.view === 'full' ? 'list' : 'full'));
controls.view.addEventListener('keydown', event => {
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault(); changeView(event.key === 'ArrowLeft' ? 'full' : 'list');
  }
});
for (const key of ['tier', 'type']) controls[key].addEventListener('click', event => {
  const button = event.target.closest('button[data-value]');
  if (!button) return;
  const selected = new Set(state[key].split(',').filter(Boolean));
  const value = button.dataset.value;
  if (!value) selected.clear();
  else if (selected.has(value)) selected.delete(value);
  else selected.add(value);
  state[key] = [...selected].sort().join(',');
  controls[key].closest('details').querySelector('.selection-count').textContent = selected.size ? ` (${selected.size})` : '';
  for (const option of controls[key].querySelectorAll('button')) option.setAttribute('aria-pressed', String(option.dataset.value ? selected.has(option.dataset.value) : selected.size === 0));
  history.replaceState(null, '', location.pathname + location.search);
  writeURL(); render();
});
function closeDropdowns(except) {
  form.querySelectorAll('.filter-dropdown').forEach(dropdown => { if (dropdown !== except) dropdown.open = false; });
}
for (const dropdown of form.querySelectorAll('.filter-dropdown')) dropdown.addEventListener('toggle', () => {
  if (!dropdown.open) return;
  closeDropdowns(dropdown);
  const rect = dropdown.getBoundingClientRect();
  const menu = dropdown.querySelector('.filter-chips');
  menu.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - 228))}px`;
  menu.style.top = `${Math.min(rect.bottom + 5, innerHeight - 240)}px`;
});
document.addEventListener('click', event => { if (!event.target.closest('.filter-dropdown')) closeDropdowns(); });
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeDropdowns(); });
form.addEventListener('scroll', () => closeDropdowns());
window.addEventListener('resize', () => closeDropdowns());
window.addEventListener('scroll', () => closeDropdowns());
form.addEventListener('reset', event => {
  event.preventDefault();
  closeDropdowns();
  state = {...defaults};
  history.replaceState(null, '', location.pathname);
  localize(); render(true);
});
// A hoverable, scrollable preview remains open while moving from the entry to it.
const preview = document.createElement('aside');
preview.className = `stat-card adversary-preview${environment ? ' environment-card' : ''}`;
preview.id = 'adversary-preview'; preview.hidden = true;
preview.setAttribute('role', 'dialog');
preview.setAttribute('aria-label', environment ? '完整环境卡片 / Full environment' : '完整敌人卡片 / Full adversary');
document.body.append(preview);
let previewSource = null;
let closeTimer;
let dismissed = false;
function closePreview() {
  clearTimeout(closeTimer);
  preview.hidden = true;
  previewSource?.removeAttribute('aria-expanded');
  previewSource = null;
}
function showPreview(card) {
  if (state.view !== 'list' || innerWidth < 600) return;
  clearTimeout(closeTimer);
  const trigger = card.querySelector('.compact-name');
  if (previewSource === trigger && !preview.hidden) return;
  closePreview(); previewSource = trigger;
  const content = card.querySelector(`.srd-language.lang-${language()}`).cloneNode(true);
  content.querySelectorAll('[id], [data-anchor]').forEach(element => { element.removeAttribute('id'); element.removeAttribute('data-anchor'); });
  const close = document.createElement('button');
  close.type = 'button'; close.className = 'preview-close'; close.textContent = '×';
  close.setAttribute('aria-label', language() === 'zh' ? '关闭预览' : 'Close preview');
  close.addEventListener('click', () => { dismissed = true; closePreview(); });
  preview.replaceChildren(close, content);
  preview.hidden = false; trigger.setAttribute('aria-expanded', 'true');
  const rect = card.getBoundingClientRect();
  const width = preview.getBoundingClientRect().width;
  const left = rect.right + 10 + width <= innerWidth ? rect.right + 10 : Math.max(8, rect.left - width - 10);
  preview.style.left = `${Math.min(left, innerWidth - width - 8)}px`;
  preview.style.top = `${Math.max(72, Math.min(rect.top, innerHeight - preview.offsetHeight - 8))}px`;
}
function scheduleClose() { clearTimeout(closeTimer); closeTimer = setTimeout(closePreview, 180); }
for (const card of cards) {
  card.addEventListener('pointerenter', event => { if (event.pointerType === 'mouse' && !dismissed) showPreview(card); });
  card.addEventListener('pointerleave', scheduleClose);
  card.querySelector('.compact-name').addEventListener('focus', () => { dismissed = false; showPreview(card); });
  card.querySelector('.compact-name').setAttribute('aria-controls', preview.id);
  card.querySelector('.compact-name').setAttribute('aria-haspopup', 'dialog');
}
preview.addEventListener('pointerenter', () => clearTimeout(closeTimer));
preview.addEventListener('pointerleave', scheduleClose);
document.addEventListener('focusin', event => {
  if (!preview.hidden && event.target !== previewSource && !preview.contains(event.target)) closePreview();
});
document.addEventListener('keydown', event => { if (event.key === 'Escape') { dismissed = true; closePreview(); } });
document.addEventListener('pointermove', event => { if (event.movementX || event.movementY) dismissed = false; });
window.addEventListener('resize', closePreview);
window.addEventListener('scroll', closePreview);
new MutationObserver(() => { localize(); render(); openHash(); }).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
window.addEventListener('hashchange', openHash);
window.addEventListener('popstate', () => { readURL(); localize(); render(true); openHash(); });
readURL(); localize(); render(true); openHash();
form.hidden = false;
