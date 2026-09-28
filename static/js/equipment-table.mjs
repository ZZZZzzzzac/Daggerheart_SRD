import { compareEquipment, normalizeEquipment } from './equipment-core.mjs?v=20260928-loot';

const catalogs = [...document.querySelectorAll('.equipment-catalog')].map(element => ({
  element, language:element.dataset.language,
  table:element.querySelector('table'),
  headers:[...element.querySelectorAll('th')],
  rows:[...element.querySelectorAll('tbody tr')].map((element, index) => ({element,index,cells:Object.fromEntries([...element.cells].map(cell => [cell.dataset.column,cell]))})),
}));
const filters = new Map();
const sorts = [];
let popover = null, trigger = null;
const node = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};
const icon = (name) => {
  const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox','0 0 24 24');
  svg.setAttribute('aria-hidden','true');
  svg.setAttribute('class',`equipment-icon equipment-icon-${name}`);
  const path = document.createElementNS(svg.namespaceURI,'path');
  path.setAttribute('d',name === 'chevron' ? 'm6 9 6 6 6-6' : name === 'search' ? 'M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13Zm4.7-1.8L21 21' : 'm7 9 5-5 5 5M12 4v16m-5-5 5 5 5-5');
  svg.append(path);
  return svg;
};

function closeFilter(focus = false) {
  popover?.remove();
  popover = null;
  trigger?.setAttribute('aria-expanded', 'false');
  if (focus) trigger?.focus();
  trigger = null;
}

function render() {
  for (const catalog of catalogs) {
    const ordered = [...catalog.rows];
    if (sorts.length) ordered.sort((a,b) => {
      for (const sort of sorts) {
        const numeric = ['tier','range','damage','thresholds','armor','roll'].includes(sort.key);
        const value = row => numeric ? row.cells[sort.key].dataset.value : row.cells[sort.key].textContent;
        const result = sort.direction * compareEquipment(value(a),value(b),sort.key,catalog.language);
        if (result) return result;
      }
      return a.index - b.index;
    });
    let shown = 0;
    for (const row of ordered) {
      const visible = [...filters].every(([key, filter]) => {
        const cell = row.cells[key];
        const searchable = ['damage','thresholds','roll'].includes(key) ? normalizeEquipment(cell.textContent) : cell.dataset.search;
        return typeof filter === 'string' ? searchable.includes(normalizeEquipment(filter)) : filter.has(cell.dataset.value);
      });
      row.element.hidden = !visible;
      if (visible) shown++;
    }
    catalog.table.tBodies[0].append(...ordered.map(row => row.element));
    catalog.count.textContent = catalog.language === 'zh' ? `${shown} / ${ordered.length} ${catalog.element.dataset.queryOnly === 'true' ? '条' : '件装备'}` : `${shown} / ${ordered.length} items`;
    catalog.element.querySelector('.equipment-empty').hidden = shown !== 0;
    for (const header of catalog.headers) {
      const key = header.dataset.column;
      const priority = sorts.findIndex(sort => sort.key === key);
      const sort = sorts[priority];
      const direction = sort?.direction === 1 ? 'ascending' : 'descending';
      header.setAttribute('aria-sort', sort ? (priority === 0 ? direction : 'other') : 'none');
      header.dataset.sortPriority = sort ? String(priority + 1) : '';
      header.dataset.sortDirection = sort ? direction : '';
      const mark = header.querySelector('.equipment-sort-mark');
      mark.replaceChildren(sort ? node('span',sort.direction === 1 ? '↑' : '↓') : icon('sort'));
      const action = header.querySelector('.equipment-sort-button');
      action.classList.toggle('is-active',Boolean(sort));
      action.setAttribute('aria-description',sort
        ? (catalog.language === 'zh' ? `排序优先级 ${priority + 1}，${sort.direction === 1 ? '升序' : '降序'}` : `Sort priority ${priority + 1}, ${direction}`)
        : (catalog.language === 'zh' ? '点击添加升序排序' : 'Add ascending sort'));
      header.querySelector('.equipment-filter-button').classList.toggle('is-active', filters.has(key));
    }
    catalog.sortSummary.textContent = sorts.length
      ? (catalog.language === 'zh' ? '排序：' : 'Sort: ') + sorts.map((sort,i) => `${i+1} ${catalog.headers.find(h=>h.dataset.column===sort.key).dataset.label} ${sort.direction===1?'↑':'↓'}`).join(' · ')
      : (catalog.language === 'zh' ? '依次点击列名叠加排序：升序 → 降序 → 取消' : 'Click columns to add sorting: ascending → descending → off');
    catalog.reset.disabled = !filters.size && !sorts.length;
  }
}

function openFilter(catalog, header, button) {
  const wasOpen = trigger === button;
  closeFilter();
  if (wasOpen) return;
  trigger = button;
  button.setAttribute('aria-expanded','true');
  const key = header.dataset.column, zh = catalog.language === 'zh';
  const query = header.dataset.filter === 'text';
  const verb = zh ? (query ? '查询' : '筛选') : (query ? 'Search' : 'Filter');
  popover = node('div', undefined, 'equipment-filter-popover');
  popover.setAttribute('role','dialog');
  popover.setAttribute('aria-label', `${verb} ${header.dataset.label}`);
  const heading = node('div', undefined, 'equipment-filter-heading');
  heading.append(node('strong',`${verb} ${header.dataset.label}`));
  const close = node('button','×');
  close.type = 'button';
  close.setAttribute('aria-label',zh ? '关闭筛选' : 'Close filter');
  close.addEventListener('click',() => closeFilter(true));
  heading.append(close);
  popover.append(heading);
  if (header.dataset.filter === 'text') {
    const input = node('input');
    input.type = 'search';
    input.placeholder = key === 'damage' ? (zh ? '例如 d8、d10+3' : 'e.g. d8, d10+3') : key === 'thresholds' ? (zh ? '例如 11、11 / 24' : 'e.g. 11, 11 / 24') : key === 'roll' ? (zh ? '例如 01、22' : 'e.g. 01, 22') : (zh ? '输入中文或英文…' : 'Chinese or English…');
    input.setAttribute('aria-label', header.dataset.label);
    input.value = filters.get(key) || '';
    input.addEventListener('input',() => {
      if (input.value.trim()) filters.set(key,input.value); else filters.delete(key);
      render();
    });
    popover.append(input);
  } else {
    const choices = new Map(catalog.rows.map(row => [row.cells[key].dataset.value,key === 'damage' ? row.cells[key].dataset.value : row.cells[key].textContent.trim()]));
    const all = node('button', zh ? '全选' : 'Select all');
    const none = node('button', zh ? '全不选' : 'Select none');
    all.type = none.type = 'button';
    const actions = node('div',undefined,'equipment-filter-actions');
    actions.append(all,none);
    popover.append(actions);
    const list = node('div',undefined,'equipment-filter-choices');
    for (const [value,label] of [...choices].sort((a,b) => compareEquipment(a[0],b[0],key,catalog.language))) {
      const option = node('label');
      const input = node('input');
      input.type='checkbox'; input.value=value;
      input.checked = !filters.has(key) || filters.get(key).has(value);
      input.addEventListener('change',() => {
        const selected = new Set([...list.querySelectorAll('input:checked')].map(el => el.value));
        if (selected.size === choices.size) filters.delete(key); else filters.set(key,selected);
        render();
      });
      option.append(input,node('span',label)); list.append(option);
    }
    all.addEventListener('click',() => { filters.delete(key); list.querySelectorAll('input').forEach(el => {el.checked=true;}); render(); });
    none.addEventListener('click',() => { filters.set(key,new Set()); list.querySelectorAll('input').forEach(el => {el.checked=false;}); render(); });
    popover.append(list);
  }
  const clear = node('button',zh ? (query ? '清除此列查询' : '清除此列筛选') : 'Clear this filter','equipment-clear-column');
  clear.type='button';
  clear.addEventListener('click',() => {filters.delete(key); render(); closeFilter(true);});
  popover.append(clear);
  document.body.append(popover);
  const rect = button.getBoundingClientRect();
  const control = header.querySelector('.equipment-header-controls').getBoundingClientRect();
  popover.style.left = `${Math.max(12,Math.min(control.left + control.width / 2 - popover.offsetWidth / 2,innerWidth - popover.offsetWidth - 12))}px`;
  popover.style.top = `${Math.max(12,Math.min(rect.bottom + 6,innerHeight - popover.offsetHeight - 12))}px`;
  (popover.querySelector('input') || close).focus();
}

for (const catalog of catalogs) {
  const zh = catalog.language === 'zh';
  const toolbar = catalog.element.querySelector('.equipment-toolbar');
  catalog.count = node('p');
  catalog.count.setAttribute('role','status');
  catalog.reset = node('button',zh ? (catalog.element.dataset.queryOnly === 'true' ? '清除查询与排序' : '清除筛选与排序') : 'Reset filters and sorting','equipment-reset');
  catalog.reset.type='button';
  catalog.reset.addEventListener('click',() => {filters.clear(); sorts.length=0; closeFilter(); render();});
  catalog.sortSummary = node('p',undefined,'equipment-sort-summary');
  toolbar.append(catalog.count,catalog.reset,catalog.sortSummary);
  toolbar.hidden=false;
  for (const header of catalog.headers) {
    const label=header.textContent, key=header.dataset.column;
    header.dataset.label=label;
    const sortButton=node('button',undefined,'equipment-sort-button');
    sortButton.type='button';
    sortButton.setAttribute('aria-label',zh ? `按${label}排序` : `Sort by ${label}`);
    if (key === 'damage') sortButton.title = zh ? '按骰面，再按固定加值排序' : 'Sort by die size, then flat modifier';
    if (key === 'thresholds') sortButton.title = zh ? '先按重度阈值，再按严重阈值排序' : 'Sort by Major, then Severe threshold';
    sortButton.append(node('span',label),node('span',undefined,'equipment-sort-mark'));
    sortButton.addEventListener('click',() => {
      const index = sorts.findIndex(sort => sort.key === key);
      if (index < 0) sorts.push({key,direction:1});
      else if (sorts[index].direction === 1) sorts[index].direction = -1;
      else sorts.splice(index,1);
      closeFilter(); render();
    });
    const query = header.dataset.filter === 'text';
    const filter=node('button',undefined,'equipment-filter-button');
    filter.append(icon(query ? 'search' : 'chevron'));
    filter.type='button';
    filter.setAttribute('aria-label',zh ? `${query ? '查询' : '筛选'}${label}` : `${query ? 'Search' : 'Filter'} ${label}`);
    filter.setAttribute('aria-haspopup','dialog');
    filter.setAttribute('aria-expanded','false');
    filter.addEventListener('click',() => openFilter(catalog,header,filter));
    const controls=node('div',undefined,'equipment-header-controls');
    controls.append(sortButton,filter);
    header.replaceChildren(controls);
  }
}

function revealHash() {
  let id;
  try {id=decodeURIComponent(location.hash.slice(1));} catch {return;}
  const target=document.getElementById(id), row=target?.closest('tr');
  if (!row) return;
  if (row.hidden) {filters.clear(); render();}
  requestAnimationFrame(() => target.scrollIntoView({block:'center'}));
}
document.addEventListener('pointerdown',event => {if(popover && !popover.contains(event.target) && !trigger?.contains(event.target)) closeFilter();});
document.addEventListener('keydown',event => {if(event.key==='Escape' && popover) {event.preventDefault();closeFilter(true);}});
document.addEventListener('focusin',event => {if(popover && !popover.contains(event.target) && event.target!==trigger) closeFilter();});
window.addEventListener('resize',() => closeFilter());
window.addEventListener('scroll',event => {if(popover && !popover.contains(event.target)) closeFilter();},true);
window.addEventListener('hashchange',revealHash);
new MutationObserver(() => {closeFilter();render();revealHash();}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
render();
revealHash();
