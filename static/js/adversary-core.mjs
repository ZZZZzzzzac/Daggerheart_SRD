// The reader and editor share this Markdown card renderer. Markers carry identity only.
export const adversaryTypes = {bruiser: '斗士', horde: '集群', leader: '头目', minion: '杂兵', ranged: '远程', skulk: '潜伏', social: '社交', solo: '独狼', standard: '标准', support: '辅助'};
const plain = value => value.replace(/<[^>]*>/g, '').replace(/&amp;/g, '&').trim();
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

export function renderAdversaries(html, language) {
  const seen = new Set();
  const openings = (html.match(/<!-- adversary:/g) || []).length;
  let count = 0;
  const output = html.replace(/<!-- adversary: ([a-z][a-z0-9-]*) \| ([^\n]*?) -->\s*([\s\S]*?)<!-- \/adversary -->/g, (_, id, english, body) => {
    if (seen.has(id)) throw new Error(`敌人 ID 重复：${id}`);
    seen.add(id); count++;
    const title = body.match(/^<h[2-5]\b[^>]*>[\s\S]*?<\/h[2-5]>/);
    if (!title) throw new Error(`敌人缺少名称标题：${id}`);
    const name = plain(title[0]);
    body = body.slice(title[0].length);
    const role = body.match(/^\s*(?:<h5\b[^>]*>[\s\S]*?<\/h5>|<p><em>Tier[\s\S]*?<\/em><\/p>)/);
    const roleText = plain(role?.[0] || '');
    const tier = roleText.match(/位阶\s*([1-4])/)?.[1] || '';
    const kind = language === 'zh' ? Object.keys(adversaryTypes).find(key => roleText.includes(adversaryTypes[key])) : roleText.match(/Tier\s*(?:[1-4]\s*)?([A-Za-z]+)/)?.[1]?.toLowerCase();
    if (!kind || (language === 'zh' && !tier)) throw new Error(`敌人缺少位阶或类型：${name}`);
    body = body.slice(role?.[0].length || 0);
    const difficulty = plain(body).match(/(?:难度|Difficulty)[：:]\s*(\d+)/)?.[1];
    if (!difficulty) throw new Error(`敌人缺少难度：${name}`);
    // Two legacy English stat lines are fenced code; normalize their presentation too.
    body = body.replace(/<pre><code>(Difficulty:[\s\S]*?)<\/code><\/pre>/g, (_block, content) => content.trim().split('\n').map(line => `<p>${line.replace(/(^|\|\s*)([^:|]+:)/g, '$1<strong>$2</strong>')}</p>`).join('\n'));
    // Separate the original hard-break metadata lines; their inline Markdown stays intact.
    body = body.replace(/<p>([\s\S]*?)<\/p>/g, (_p, content) => content.split(/<br\s*\/?>\s*/).map(line => `<p>${line}</p>`).join('\n'));
    let values = '', resources = '';
    body = body.replace(/<p>([\s\S]*?)<\/p>/g, (paragraph, content) => {
      if (/^<strong>(?:难度|Difficulty)[：:]/.test(content)) {
        const at = content.indexOf('<strong>ATK:');
        const stats = at < 0 ? content : content.slice(0, at);
        const cells = stats.split('|');
        values = `<div class="stat-values">${cells.slice(0, 2).map(cell => `<span>${cell.trim()}</span>`).join('')}</div>`;
        resources = `<div class="stat-resources">${cells.slice(2).map(cell => `<span>${cell.trim()}</span>`).join('')}</div>`;
        return at < 0 ? '' : `<p class="stat-attack">${content.slice(at)}</p>`;
      }
      if (/^<strong>(?:攻击|ATK)[：:]/.test(content)) return `<p class="stat-attack">${content}</p>`;
      if (/^<strong>(?:经历|Experiences?)[：:]/.test(content)) return `<p class="stat-experience">${content}</p>`;
      return paragraph;
    });
    let description = '';
    body = body.replace(/^\s*<p>(<em>[\s\S]*?<\/em>)([\s\S]*?)<\/p>/, (_, summary, rest) => {
      description = `<p class="stat-description">${summary}</p>`;
      return rest.trim() ? `<p>${rest.trim()}</p>` : '';
    });
    const take = pattern => {
      const found = body.match(pattern)?.[0] || '';
      body = body.replace(pattern, '');
      return found;
    };
    const motives = take(/<p><strong>(?:动机与战术|Motives &amp; Tactics)[：:][\s\S]*?<\/p>/);
    const experience = take(/<p class="stat-experience">[\s\S]*?<\/p>/);
    const attack = take(/<p class="stat-attack">[\s\S]*?<\/p>/);
    const brief = `<div class="stat-brief"><div class="stat-motives">${motives}${experience}</div>${values}</div>`;
    body = body.replace(/(<(?:li|p)>\s*)<em>/g, '$1<em class="no-glossary">');
    const heading = title[0].replace(/<h[2-5]/, '<h3').replace(/<\/h[2-5]>/, '</h3>');
    return `<article class="stat-card" data-card-id="${id}" data-tier="${tier}" data-type="${kind}" data-name="${escape(name)}" data-name-en="${escape(english)}" data-difficulty="${difficulty}"><header class="stat-heading no-glossary">${heading}<div class="stat-role">${role?.[0] || ''}</div>${description}</header><div class="stat-content"><div class="stat-meta no-glossary">${brief}${attack}${resources}</div><div class="stat-features">${body}</div></div></article>`;
  });
  if (count !== openings || count !== (html.match(/<!-- \/adversary -->/g) || []).length) throw new Error('敌人卡片标记不完整，请检查开始和结束标记');
  return output;
}
