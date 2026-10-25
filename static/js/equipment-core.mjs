// 正文和编辑器共用：从 Markdown 渲染结果组装表格，不另存装备数据。
export const equipmentRoot = 'core-mechanics/equipment';
export const equipmentKinds = ['primary-weapons', 'secondary-weapons', 'armor', 'items', 'consumables'];
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const plain = value => value.replace(/<br\s*\/?>/gi, ' ').replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ').trim();
export const normalizeEquipment = value => String(value).toLowerCase().replace(/\s+/g, '').trim();

export function compareEquipment(left, right, key, language = 'zh') {
  const nums = value => (String(value).match(/\d+/g) || []).map(Number);
  if (['tier', 'armor', 'thresholds', 'damage', 'roll'].includes(key)) {
    const a = nums(left), b = nums(right);
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      const diff = (a[i] || 0) - (b[i] || 0);
      if (diff) return diff;
    }
    return 0;
  }
  if (key === 'range') {
    const order = ['melee','very close','close','far','very far'];
    return order.indexOf(left.toLowerCase()) - order.indexOf(right.toLowerCase());
  }
  return String(left).localeCompare(String(right), language === 'zh' ? 'zh-CN' : 'en', {numeric:true});
}

function parseTables(html, kind) {
  const tokens = [...html.matchAll(/<h([1-6])\b([^>]*)>([\s\S]*?)<\/h\1>|<table\b[^>]*>[\s\S]*?<\/table>/g)];
  const firstHeading = tokens.find(t => t[1]);
  const secondHeading = tokens.filter(t => t[1])[1];
  const intro = secondHeading ? html.slice(0, secondHeading.index) : '';
  const mainAnchor = firstHeading?.[2].match(/data-anchor="([^"]+)"/)?.[1];
  let tier = '', type = '', pending = [];
  const tables = [];
  for (const token of tokens) {
    if (token[1]) {
      const text = plain(token[3]);
      const anchor = token[2].match(/data-anchor="([^"]+)"/)?.[1];
      if (anchor && anchor !== mainAnchor) pending.push(anchor);
      tier = text.match(/(?:位阶|TIER)\s*([1-4])/i)?.[1] || tier;
      if (/物理武器|physical weapons/i.test(text)) type = 'physical';
      if (/魔法武器|magic weapons/i.test(text)) type = 'magic';
      continue;
    }
    const body = token[0].match(/<tbody>([\s\S]*?)<\/tbody>/)?.[1] || '';
    const rows = [...body.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].map(row => [...row[1].matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/g)].map(c => c[1]));
    const filled = rows.filter(row => row.some(cell => plain(cell)));
    if (!tier || (kind === 'primary-weapons' && !type)) throw new Error('装备表缺少位阶或武器类型');
    for (const row of filled) if (row.length !== (kind === 'armor' ? 4 : 6) || !plain(row[0])) throw new Error('装备表列数或名称无效');
    tables.push({tier, type, anchors:pending, rows:filled});
    pending = [];
  }
  return {intro, tables};
}

export function renderEquipmentPair(html, kind) {
  if (['items','consumables'].includes(kind)) return renderLootPair(html,kind);
  const parsed = Object.fromEntries(['zh','en'].map(lang => [lang, parseTables(html[lang], kind)]));
  if (parsed.zh.tables.length !== parsed.en.tables.length) throw new Error('中英文装备表数量不一致');
  const columns = kind === 'armor' ? ['name','tier','thresholds','armor','feature'] : ['name','tier','trait','range','damage','type','burden','feature'];
  const labels = {
    zh: {name:'名称',tier:'位阶',type:'类型',trait:'属性',range:'距离',damage:'伤害',burden:'负荷',thresholds:'阈值',armor:'护甲值',feature:'特性'},
    en: {name:'Name',tier:'Tier',type:'Type',trait:'Trait',range:'Range',damage:'Damage',burden:'Burden',thresholds:'Thresholds',armor:'Armor score',feature:'Feature'},
  };
  const ids = new Set();
  const rows = {zh:[], en:[]};
  parsed.zh.tables.forEach((zhTable, tableIndex) => {
    const enTable = parsed.en.tables[tableIndex];
    if (zhTable.rows.length !== enTable.rows.length || zhTable.tier !== enTable.tier || zhTable.type !== enTable.type) throw new Error(`中英文装备表条目或位阶不一致：第 ${tableIndex + 1} 表`);
    zhTable.rows.forEach((_, rowIndex) => {
      const enName = plain(enTable.rows[rowIndex][0]);
      const id = `gear-tier-${enTable.tier}-${enName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`;
      if (ids.has(id)) throw new Error(`装备名称重复：${enName}`);
      ids.add(id);
      const values = {};
      // 类型读取每条原文的伤害字段，兼容“phy or mag”，不按整页假定。
      const originalDamage = plain(enTable.rows[rowIndex][3]);
      const types = ['phy','mag'].filter(type => new RegExp(`\\b${type}\\b`, 'i').test(originalDamage));
      if (kind !== 'armor' && !types.length) throw new Error(`武器伤害缺少物理/魔法类型：${enName}`);
      for (const lang of ['zh','en']) {
        const table = parsed[lang].tables[tableIndex], cells = table.rows[rowIndex];
        values[lang] = kind === 'armor'
          ? {name:cells[0],tier:table.tier,thresholds:cells[1],armor:cells[2],feature:cells[3]}
          : {name:cells[0],tier:table.tier,type:types.map(type=>lang==='zh' ? (type==='phy'?'物理':'魔法') : (type==='phy'?'Physical':'Magic')).join(' / '),trait:cells[1],range:cells[2],damage:cells[3].replace(/\b(?:phy|mag)(?:\s+or\s+(?:phy|mag))?\b/gi,'').trim(),burden:cells[4],feature:cells[5]};
      }
      for (const lang of ['zh','en']) {
        const anchors = rowIndex === 0 ? parsed[lang].tables[tableIndex].anchors : [];
        const aliases = anchors.map(a => `<span data-anchor="${a}"${lang === 'zh' ? ` id="${a}"` : ''}></span>`).join('');
        const cells = columns.map(key => {
          const english = plain(values.en[key]);
          const visible = plain(values[lang][key]);
          // 数值取正在阅读的正文，避免只改中文数值后仍按旧英文值排序。
          const canonical = key === 'damage' ? (visible.match(/d\d+(?:\s*[+-]\s*\d+)?/i)?.[0].replace(/\s+/g, '') || visible)
            : ['tier','armor','thresholds'].includes(key) ? visible.replace(/\s+/g, '') : english;
          const search = normalizeEquipment(plain(values.zh[key]) + ' ' + english);
          const content = values[lang][key] || '—';
          return `<td data-column="${key}" data-value="${escape(canonical)}" data-search="${escape(search)}">${key === 'name' ? aliases + `<a href="#${id}">${content}</a>` : content}</td>`;
        }).join('');
        rows[lang].push(`<tr data-anchor="${id}"${lang === 'zh' ? ` id="${id}"` : ''}>${cells}</tr>`);
      }
    });
  });
  return Object.fromEntries(['zh','en'].map(lang => [lang,catalogHTML(parsed[lang].intro,rows[lang],columns,labels[lang],lang)]));
}

function catalogHTML(intro,rows,columns,labels,lang,queryOnly=false) {
  const headers = columns.map(key => `<th scope="col" data-column="${key}" data-filter="${queryOnly || ['name','feature','damage','thresholds'].includes(key) ? 'text' : 'choices'}">${labels[key]}</th>`).join('');
  return `${intro}<section class="equipment-catalog" data-language="${lang}" data-query-only="${queryOnly}"><div class="equipment-toolbar" hidden></div><div class="equipment-scroll" role="region" aria-label="${lang === 'zh' ? '装备表格，可横向滚动' : 'Equipment table, scroll horizontally'}" tabindex="0"><table class="equipment-table"><thead><tr>${headers}</tr></thead><tbody>${rows.join('')}</tbody></table></div><p class="equipment-empty" hidden>${lang === 'zh' ? '没有符合条件的条目，请调整或清除查询条件。' : 'No matching items. Adjust or clear your search.'}</p></section>`;
}

function renderLootPair(html,kind) {
  const parsed = {};
  for (const lang of ['zh','en']) {
    const firstTable = html[lang].indexOf('<div class="table-scroll"');
    if (firstTable<0) throw new Error(`物品页面缺少表格：${kind}`);
    const rows = new Map();
    let group = 'core';
    for (const token of html[lang].matchAll(/<h[1-6]\b[^>]*data-anchor="loot-group-([a-z-]+)"[^>]*>[\s\S]*?<\/h[1-6]>|<table\b[^>]*>([\s\S]*?)<\/table>/g)) {
      if (token[1]) { group = token[1]; continue; }
      const table = [token[0], token[2]];
      for (const row of table[1].matchAll(/<tr>([\s\S]*?)<\/tr>/g)) {
        const cells = [...row[1].matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/g)].map(m=>m[1]);
        // 英文原文有左右并列的三列表格，以及空的占位列；按掷骰编号配对。
        for (let i=0;i+2<cells.length;i+=3) {
          if (![cells[i],cells[i+1],cells[i+2]].some(plain)) continue;
          const roll = plain(cells[i]);
          if (!/^\d+$/.test(roll) || !plain(cells[i+1])) throw new Error(`物品编号或名称无效：${kind} ${roll}`);
          const key = `${group}:${Number(roll)}`;
          if (rows.has(key)) throw new Error(`物品编号重复：${kind} ${key}`);
          rows.set(key,{roll:escape(roll),name:cells[i+1],feature:cells[i+2],group,source:group==='core'?(lang==='zh'?'核心规则':'Core Rules'):(lang==='zh'?'希望与恐惧':'Hope & Fear')});
        }
      }
    }
    parsed[lang] = {intro:html[lang].slice(0,firstTable),rows};
  }
  if (parsed.zh.rows.size!==parsed.en.rows.size || [...parsed.zh.rows.keys()].some(key=>!parsed.en.rows.has(key))) throw new Error(`中英文物品编号不一致：${kind}`);
  const grouped = new Set([...parsed.zh.rows.values()].map(r=>r.group)).size>1;
  const columns=grouped?['name','source','roll','feature']:['name','roll','feature'];
  const labels={zh:{name:'名称',roll:'掷骰编号',feature:'效果',source:'来源'},en:{name:'Name',roll:'Roll',feature:'Effect',source:'Source'}};
  return Object.fromEntries(['zh','en'].map(lang=>{
    const rows=[...parsed[lang].rows].sort((a,b)=>(a[1].group==='core'?0:1)-(b[1].group==='core'?0:1)||Number(a[1].roll)-Number(b[1].roll)).map(([key,values])=>{
      const id=`${kind}-${values.group==='core'?'':values.group+'-'}${String(values.roll).padStart(2,'0')}`;
      const cells=columns.map(column=>{
        const search=normalizeEquipment(plain(parsed.zh.rows.get(key)[column])+' '+plain(parsed.en.rows.get(key)[column]));
        const value=column==='roll'?String(Number(values.roll)):plain(parsed.en.rows.get(key)[column]);
        return `<td data-column="${column}" data-value="${escape(value)}" data-search="${escape(search)}">${column==='name'?`<a href="#${id}">${values[column]}</a>`:values[column]}</td>`;
      }).join('');
      return `<tr data-anchor="${id}"${lang==='zh'?` id="${id}"`:''}>${cells}</tr>`;
    });
    return [lang,catalogHTML(parsed[lang].intro,rows,columns,labels[lang],lang,true)];
  }));
}

// Inline weapon and armor tables retain their content and grouping, without controls.
export function renderStaticEquipmentTables(html, language) {
  const aliases = {
    '名称':'name', 'name':'name', '位阶':'tier', 'tier':'tier',
    '类型':'category', 'type':'category', '属性':'trait', 'trait':'trait',
    '范围':'range', '距离':'range', 'range':'range', '伤害':'damage', 'damage':'damage',
    '负荷':'burden', 'burden':'burden', '特性':'feature', 'feature':'feature',
    '阈值':'thresholds', 'thresholds':'thresholds', 'base thresholds':'thresholds',
    '重度伤害阈值':'major-threshold', '严重伤害阈值':'severe-threshold',
    '护甲值':'armor', 'armor score':'armor', 'base score':'armor',
  };
  return html.replace(/<div class="table-scroll" role="region">(<table\b[^>]*>[\s\S]*?<\/table>)<\/div>/g, (original, table) => {
    const header = table.match(/<thead>([\s\S]*?)<\/thead>/)?.[1] || '';
    const columns = [...header.matchAll(/<th\b[^>]*>([\s\S]*?)<\/th>/g)].map(cell => aliases[plain(cell[1]).toLowerCase()]);
    if (columns[0] !== 'name' || columns.some(key => !key) || !columns.includes('feature') ||
        !(columns.includes('damage') && columns.includes('burden') || columns.includes('armor'))) return original;
    const decorated = table.replace('<table>', '<table class="equipment-table">').replace(/<tr>([\s\S]*?)<\/tr>/g, (row, content) => {
      const cells = [...content.matchAll(/<(th|td)\b([^>]*)>([\s\S]*?)<\/\1>/g)];
      if (cells.length !== columns.length) return row;
      return '<tr>' + cells.map((cell, index) => {
        const key = columns[index];
        // English source tables sometimes list four tiers in the same numeric cell.
        const value = ['damage','thresholds','armor'].includes(key) ? cell[3].replace(/\s+(?=Tier [1-4]:)/g, '<br>') : cell[3];
        return `<${cell[1]}${cell[2]}${cell[1] === 'th' ? ' scope="col"' : ''} data-column="${key}">${value}</${cell[1]}>`;
      }).join('') + '</tr>';
    });
    return `<div class="equipment-scroll equipment-static" role="region" aria-label="${language === 'zh' ? '装备表格，可横向滚动' : 'Equipment table, scroll horizontally'}" tabindex="0">${decorated}</div>`;
  });
}
