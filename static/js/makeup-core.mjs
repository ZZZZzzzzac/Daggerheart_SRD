// Keep resource semantics aligned with translation-pipeline/scripts/makeup.py.
// The renderer adds emphasis, while the source normalizer only standardizes text.
export function transformProse(text, transform) {
  const spans = [];
  const lines = text.match(/[^\n]*\n|[^\n]+$/g) || [];
  let offset = 0, fence = null, start = 0;
  let frontmatter = lines[0]?.trim() === '---';
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (frontmatter) {
      if (i && ['---', '...'].includes(line.trim())) {
        spans.push([0, offset + line.length]); frontmatter = false;
      }
      offset += line.length; continue;
    }
    const marker = line.match(/^ {0,3}(`{3,}|~{3,})(.*)/);
    if (fence) {
      if (marker && marker[1][0] === fence[0] && marker[1].length >= fence.length && !marker[2].trim()) {
        spans.push([start, offset + line.length]); fence = null;
      }
    } else if (marker) {
      fence = marker[1]; start = offset;
    } else if (/^(?: {4}|\t| {0,3}#{1,6}\s| {0,3}\[[^\]]+\]:)/.test(line)) {
      spans.push([offset, offset + line.length]);
    }
    offset += line.length;
  }
  if (fence) spans.push([start, text.length]);
  if (frontmatter) spans.push([0, text.length]);
  for (const m of text.matchAll(/<!--[\s\S]*?-->|<(pre|code|script|style)\b[^>]*>[\s\S]*?<\/\1\s*>|<[^>\n]+>|https?:\/\/[^\s<>]+/gi)) spans.push([m.index, m.index + m[0].length]);
  for (const m of text.matchAll(/(`+)(?!`)(.*?)(?<!`)\1(?!`)/gs)) spans.push([m.index, m.index + m[0].length]);
  const closing = (pos, opening, ending) => {
    let depth = 0;
    for (let j = pos; j < text.length; j++) {
      if (j && text[j - 1] === '\\') continue;
      if (text[j] === opening) depth++;
      else if (text[j] === ending && --depth === 0) return j + 1;
    }
    return null;
  };
  for (let pos = 0; pos < text.length;) {
    if (text[pos] !== '[' || (pos && text[pos - 1] === '\\')) { pos++; continue; }
    const end = closing(pos, '[', ']');
    if (end && ['(', '['].includes(text[end])) {
      const tail = closing(end, text[end], text[end] === '(' ? ')' : ']');
      if (tail) { spans.push([pos && text[pos - 1] === '!' ? pos - 1 : pos, tail]); pos = tail; continue; }
    }
    if (end) { spans.push([pos, end]); pos = end; } else pos++;
  }
  spans.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const [a, b] of spans) {
    const last = merged.at(-1);
    if (last && a <= last[1]) last[1] = Math.max(last[1], b);
    else merged.push([a, b]);
  }
  let last = 0, out = '';
  for (const [a, b] of merged) { out += transform(text.slice(last, a)) + text.slice(a, b); last = b; }
  return out + transform(text.slice(last));
}

const space = String.raw`[ \t]*(?:\*\*[ \t]*)*`;
const number = String.raw`(?:\d*[dD]\d+(?:[ \t]*[+\-−][ \t]*\d+)?|\d+|[一二三四五六七八九十两]{1,3})`;
const amount = String.raw`(?:(?:至少|至多|最多|最少)[ \t]*)?${number}(?:[ \t]*(?:或更多|或更少))?|等量的|任意数量的|所有|全部|其余的|剩余的|最后一个`;
const base = '生命|希望|压力|恐惧|绝望|恩宠|专注|回响|充能';
const resource = String.raw`(?:(?:${base})(?:点|值|槽)(?![点值槽骰池数上限])|护甲(?:槽|值|点)(?![点值槽骰池数上限])|(?:${base}|护甲)(?![\u3400-\u9fffA-Za-z0-9_]))`;
const phrasePattern = new RegExp(String.raw`(恢复|回复|标记|清除|移除|获得|花费|消耗|失去|承受)${space}(${amount})${space}(?:个|点)?${space}(${resource})`, 'g');
const digits = Object.fromEntries([...'零一二三四五六七八九'].map((c, i) => [c, i]));
digits['两'] = 2;
function normalizeNumber(value) {
  if (value in digits) return String(digits[value]);
  if (value.includes('十')) {
    const [left, right, extra] = value.split('十');
    if (extra === undefined && (!left || left in digits) && (!right || right in digits)) return String((digits[left] ?? 1) * 10 + (digits[right] ?? 0));
  }
  return value;
}

export function formatResourcePhrases(text, { bold = true } = {}) {
  return text.replace(phrasePattern, (match, rawVerb, rawAmount, rawResource, offset, source) => {
    let verb = rawVerb, amount = rawAmount, resource = rawResource;
    if (/(?:恢复|回复|清除|移除)[ \t]*(?:和|与|或|并)[ \t]*$/.test(source.slice(0, offset))) return match;
    if (/^[ \t]*(?:和|与|及|或)[ \t]*(?:生命|希望|压力|恐惧|护甲)/.test(source.slice(offset + match.length))) return match;
    const stars = (match.match(/\*\*/g) || []).length;
    if (stars % 2) return match;
    if (resource === '护甲') {
      if (!['标记', '恢复', '回复', '清除', '移除'].includes(verb)) return match;
      resource = '护甲槽';
    } else if (resource === '护甲点') resource = '护甲槽';
    else if (resource === '生命值') resource = '生命点';
    else if (base.split('|').includes(resource)) resource += '点';
    if (resource.endsWith('值') || (resource.endsWith('槽') && resource !== '护甲槽')) return match;
    resource = resource.replace('绝望点', '恐惧点');
    verb = { 回复: '恢复', 消耗: '花费' }[verb] ?? verb;
    if (['清除', '移除'].includes(verb) && resource === '生命点') verb = '恢复';
    else if (['恢复', '移除'].includes(verb) && ['压力点', '护甲槽'].includes(resource)) verb = '清除';
    else if (verb === '移除') verb = '清除';
    if (amount !== '最后一个') amount = amount.replace(/[一二三四五六七八九十两]+/g, normalizeNumber);
    amount = amount.replace(/\s*([dD+\-−])\s*/g, (_, op) => op.toLowerCase().replace('−', '-'))
      .replace(/^(至少|至多|最多|最少)\s*/, '$1 ').replace(/\s*(或更多|或更少)$/, ' $1');
    const phrase = `${verb} ${amount} ${resource}`;
    const alreadyStrong = (source.slice(0, offset).match(/\*\*/g) || []).length % 2;
    return (bold || stars) && !alreadyStrong ? `**${phrase}**` : phrase;
  });
}

export function replaceKeywords(text) {
  return text.replace(/(?<![A-Za-z0-9_(（“”‘’"'])PC(?![A-Za-z0-9_)）“”‘’"'])/g, '玩家角色')
    .replace(/(?<![A-Za-z0-9_(（“”‘’"'])GM(?![A-Za-z0-9_)）“”‘’"'])/g, '游戏主持人')
    .replace(/重骰/g, '重掷')
    .replace(/生命点值/g, '生命点')
    .replace(/恐惧点池/g, '恐惧池');
}
