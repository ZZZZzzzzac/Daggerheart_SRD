import MarkdownIt from "../vendor/markdown-it.mjs?v=15.0.1-browser";


const HEADING_RE = /^(#{1,6})\s+(.+?)\s*$/gm;
const EXPLICIT_ID_RE = /\s+\{#([a-zA-Z][\w-]*)\}\s*$/;
const TAG_RE = /<[^>]+>/g;


function cleanHeading(value) {
  return value
    .replace(EXPLICIT_ID_RE, "")
    .replace(TAG_RE, "")
    .replace(/[*_`~[\]]/g, "")
    .replaceAll("&amp;", "&")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
    .trim();
}


function slugHeading(value, fallback) {
  const explicit = value.match(EXPLICIT_ID_RE);
  if (explicit) return explicit[1].toLowerCase();
  const ascii = cleanHeading(value)
    .normalize("NFKD")
    .replace(/[^\x00-\x7f]/g, "")
    .toLowerCase();
  return ascii.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || fallback;
}


function extractHeadings(markdown) {
  return [...markdown.matchAll(HEADING_RE)].map((match) => ({
    level: match[1].length,
    raw: match[2],
    title: cleanHeading(match[2]),
  }));
}


function assignAnchorIds(zhMarkdown, enMarkdown) {
  const zhHeadings = extractHeadings(zhMarkdown);
  const enHeadings = extractHeadings(enMarkdown);
  const count = Math.max(zhHeadings.length, enHeadings.length);
  const ids = [];
  const used = new Set();
  for (let index = 0; index < count; index += 1) {
    const source = enHeadings[index]?.raw ?? zhHeadings[index].raw;
    const base = slugHeading(source, `section-${String(index + 1).padStart(3, "0")}`);
    let candidate = base;
    let suffix = 2;
    while (used.has(candidate)) {
      candidate = `${base}-${suffix}`;
      suffix += 1;
    }
    used.add(candidate);
    ids.push(candidate);
  }
  return {
    zh: ids.slice(0, zhHeadings.length),
    en: ids.slice(0, enHeadings.length),
  };
}


function formatResourcePhrases(markdown) {
  const verbs = "恢复|回复|标记|清除|移除|获得|花费|消耗|失去|承受";
  const resources = "(?:生命|希望|压力|恐惧|绝望|恩宠|专注)(?:点)?|护甲(?:槽)?";
  const amount = "\\d{1,2}d\\d{1,2}|\\d{1,2}|[一二三四五六]";
  let text = markdown.replace(
    new RegExp(`(${verbs})\\s*\\*\\*\\s*(${amount})\\s*\\*\\*\\s*\\*\\*\\s*(${resources})\\s*\\*\\*`, "g"),
    "**$1 $2 $3**",
  );
  text = text.replace(
    new RegExp(`(${verbs})\\s*\\*\\*\\s*(${amount})\\s*\\*\\*\\s*(${resources})`, "g"),
    "**$1 $2 $3**",
  );
  return text.replace(
    new RegExp(`\\*{0,2}\\s*(${verbs})\\s*(${amount})\\s*(?:点|个)?\\s*(${resources})\\s*\\*{0,2}`, "g"),
    (_, rawAction, rawAmount, rawResource) => {
      const action = { 回复: "恢复", 移除: "清除", 消耗: "花费" }[rawAction] ?? rawAction;
      const number = { 一: "1", 二: "2", 三: "3", 四: "4", 五: "5", 六: "6" }[rawAmount] ?? rawAmount;
      let resource = rawResource === "绝望" ? "恐惧" : rawResource;
      if (resource.includes("护甲")) resource = resource.endsWith("槽") ? resource : `${resource}槽`;
      else if (!resource.endsWith("点")) resource = `${resource}点`;
      return `**${action} ${number} ${resource}**`;
    },
  );
}


function boldNumbersAndDice(markdown) {
  return markdown.split("**").map((part, index) => {
    if (index % 2) return part;
    return part.replace(/([-−+]?)[ \t]*(\d*d\d+(?:[-−+][ \t]*\d+)?|\d+)/gi, (match, _sign, _value, offset) => {
      const before = offset > 0 ? part[offset - 1] : "";
      const after = part[offset + match.length] ?? "";
      if ((before === "(" && after === ")") || (before === "（" && after === "）")) return match;
      if (!/[一-龥]/.test(before) && !/[一-龥]/.test(after)) return match;
      const compact = match.replace(/\s/g, "");
      const prefix = before && !/\s/.test(before) ? " " : "";
      const suffix = after && !/\s/.test(after) ? " " : "";
      return `${prefix}**${compact}**${suffix}`;
    });
  }).join("**");
}


function applyMakeup(markdown) {
  return markdown.split("\n\n").map((paragraph) => {
    let text = paragraph
      .replace(/!\[\]\(_page.*?\)/g, "")
      .replace(/\(\(\+\+[^)]*\)\)/g, "")
      .replace(/\(\([^)]*\)\)/g, "")
      .replace(/<span.*?><\/span>/gs, "");
    text = formatResourcePhrases(text);
    text = boldNumbersAndDice(text);
    text = text.replace(/(?<=[一-龥,.，。])\*[一-龥]{1,5}\*(?=[一-龥,.，。])/g, (match) => ` ${match} `);
    return text
      .replace(/(?<![A-Za-z(（])PC(?![A-Za-z)）])/g, "玩家角色")
      .replace(/(?<![A-Za-z(（])GM(?![A-Za-z)）])/g, "游戏主持人");
  }).join("\n\n");
}


function prepareHeadings(markdown) {
  return markdown.replace(HEADING_RE, (_match, marks, title) => `${marks} ${title.replace(EXPLICIT_ID_RE, "").trimEnd()}`);
}


function createMarkdownRenderer() {
  const md = new MarkdownIt({ html: true, linkify: false, typographer: false });
  md.renderer.rules.heading_open = (tokens, index, _options, environment, renderer) => {
    const anchor = environment.anchorIds[environment.headingIndex];
    environment.headingIndex += 1;
    if (anchor) {
      if (environment.language === "zh") tokens[index].attrSet("id", anchor);
      tokens[index].attrSet("data-anchor", anchor);
    }
    return renderer.renderToken(tokens, index, {});
  };
  return md;
}


const markdownRenderer = createMarkdownRenderer();


function renderSageBlocks(markdown, language) {
  const blocks = [];
  const prepared = markdown.replace(
    /<div class="sage-touched">\s*<details>\s*<summary>(.*?)<\/summary>\s*([\s\S]*?)\s*<\/details>\s*<\/div>/g,
    (_match, summary, body) => {
      const marker = `<div data-srd-sage-placeholder="${blocks.length}"></div>`;
      blocks.push({ summary, body });
      return marker;
    },
  );
  return {
    prepared,
    restore(html) {
      return blocks.reduce((result, block, index) => {
        const body = markdownRenderer.render(
          language === "zh" ? applyMakeup(block.body) : block.body,
          { anchorIds: [], headingIndex: 0, language },
        ).trim();
        const replacement = `<div class="sage-touched">\n<details>\n<summary>${block.summary}</summary>\n${body}\n</details>\n</div>`;
        return result.replace(`<div data-srd-sage-placeholder="${index}"></div>`, replacement);
      }, html);
    },
  };
}


function renderMarkdown(markdown, anchorIds, language) {
  const withHeadings = prepareHeadings(markdown);
  const source = language === "zh" ? applyMakeup(withHeadings) : withHeadings;
  const sage = renderSageBlocks(source, language);
  let html = markdownRenderer.render(sage.prepared, {
    anchorIds,
    headingIndex: 0,
    language,
  });
  html = sage.restore(html);
  return html.replace(
    /(<table\b[^>]*>[\s\S]*?<\/table>)/g,
    '<div class="table-scroll" role="region">$1</div>',
  );
}


export function renderPair(zhMarkdown, enMarkdown) {
  const anchors = assignAnchorIds(zhMarkdown, enMarkdown);
  const headings = {
    zh: extractHeadings(zhMarkdown).map((heading, index) => ({ ...heading, anchor: anchors.zh[index] })),
    en: extractHeadings(enMarkdown).map((heading, index) => ({ ...heading, anchor: anchors.en[index] })),
  };
  return {
    anchors,
    headings,
    html: {
      zh: renderMarkdown(zhMarkdown, anchors.zh, "zh"),
      en: renderMarkdown(enMarkdown, anchors.en, "en"),
    },
  };
}


export { assignAnchorIds, extractHeadings };
