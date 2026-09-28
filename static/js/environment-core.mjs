export const environmentTypes = {traversal: '险境', exploration: '探索', event: '事件', social: '社交'};
const plain = value => value.replace(/<[^>]*>/g, '').replaceAll('&amp;', '&').trim();
const escape = value => value.replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

export function renderEnvironments(html, language) {
  const seen = new Set();
  let count = 0;
  const result = html.replace(/<!-- environment: ([a-z][a-z0-9-]*) \| ([^\n]*?) -->\s*([\s\S]*?)<!-- \/environment -->/g, (_, id, english, body) => {
    if (seen.has(id)) throw new Error(`环境 ID 重复：${id}`);
    seen.add(id); count++;
    const take = pattern => { const match = body.match(pattern)?.[0] || ''; body = body.replace(pattern, ''); return match; };
    const title = take(/^<h[2-5]\b[^>]*>[\s\S]*?<\/h[2-5]>/);
    const role = take(/^\s*<h5\b[^>]*>[\s\S]*?<\/h5>/);
    const tier = plain(role).match(/(?:位阶|Tier)\s*([1-4])/)?.[1];
    const kind = language === 'zh' ? Object.keys(environmentTypes).find(key => plain(role).includes(environmentTypes[key])) : plain(role).match(/Tier\s*[1-4]\s*(\w+)/)?.[1]?.toLowerCase();
    if (!title || !tier || !environmentTypes[kind]) throw new Error(`环境名称、位阶或类型无效：${id}`);
    body = body.replace(/<p>([\s\S]*?)<\/p>/g, (_p, content) => content.split(/<br\s*\/?>\s*/).map(line => `<p>${line}</p>`).join('\n'));
    let description = '';
    body = body.replace(/^\s*<p>(<em>[\s\S]*?<\/em>)([\s\S]*?)<\/p>/, (_p, summary, rest) => {
      description = `<p class="stat-description">${summary}</p>`;
      return rest.trim() ? `<p>${rest.trim()}</p>` : '';
    });
    body = body.replace(/<p>([\s\S]*?)<\/p>/g, (_p, content) => '<p>' + content.replace(/(?<=.)\s*(<strong>(?:Potential Adversaries|Difficulty|Impulses):)/g, '</p><p>$1') + '</p>');
    const impulse = take(/<p><strong>(?:趋向|Impulses)[：:][\s\S]*?<\/p>/);
    const opponents = take(/<p><strong>(?:潜在敌人|Potential Adversaries)[：:][\s\S]*?<\/p>/);
    const difficultyBlock = take(/<(?:p|h4)\b[^>]*>(?:<span\b[^>]*data-legacy-anchor="[^"]*"[^>]*><\/span>)*<strong>(?:难度|Difficulty)[：:][\s\S]*?<\/(?:p|h4)>/);
    const difficulty = plain(difficultyBlock).replace(/^(?:难度|Difficulty)[：:]\s*/, '').trim();
    if (!difficulty || !impulse || !opponents) throw new Error(`环境缺少难度、趋向或潜在敌人：${id}`);
    const difficultyHTML = difficultyBlock.replace(/^<(p|h4)([^>]*)>/, `<div$2 class="environment-difficulty${/^\d+$/.test(difficulty) ? '' : ' is-special'}">`).replace(/<\/(?:p|h4)>$/, '</div>');
    // Keep GM prompts with their features and distinguish them from ability names.
    body = body.replace(/<br\s*\/?>\s*(<em>[\s\S]*?<\/em>)(?=\s*(?:<\/li>|<\/p>))/g, '<div class="environment-question">$1</div>');
    body = body.replace(/<p>(<em>[^<]*[?？]<\/em>)<\/p>/g, '<p class="environment-question">$1</p>');
    body = body.replace(/(<(?:li|p)>\s*)<em>([^<]*?(?:被动|动作|反应|Passive|Action|Reaction)[^<]*?)<\/em>/g, '$1<em class="no-glossary">$2</em>');
    const heading = title.replace(/<h[2-5]/, '<h3').replace(/<\/h[2-5]>/, '</h3>');
    return `<article class="stat-card" data-card-kind="environment" data-card-id="${id}" data-tier="${tier}" data-type="${kind}" data-name="${escape(plain(title))}" data-name-en="${escape(english)}" data-difficulty="${escape(difficulty)}"><header class="stat-heading no-glossary">${heading}<div class="stat-role">${role}</div>${description}</header><div class="stat-content"><div class="environment-brief no-glossary">${difficultyHTML}<div class="environment-context">${impulse}${opponents}</div></div><div class="stat-features">${body}</div></div></article>`;
  });
  if (count !== (html.match(/<!-- environment:/g) || []).length || count !== (html.match(/<!-- \/environment -->/g) || []).length) throw new Error('环境卡片标记不完整');
  return result;
}
