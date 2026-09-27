// Match a phrase across inline markup, ignoring formatting whitespace.
const normalize = value => value.normalize('NFKC').toLowerCase().replace(/\s/g, '');

export function phraseMatches(text, query) {
  const needle = normalize(query);
  if (!needle) return [];
  let normalized = '', offset = 0;
  const positions = [];
  for (const character of text) {
    const part = normalize(character);
    for (let i = 0; i < part.length; i++) positions.push([offset, offset + character.length]);
    normalized += part;
    offset += character.length;
  }
  const matches = [];
  for (let start = normalized.indexOf(needle); start !== -1; start = normalized.indexOf(needle, start + needle.length)) {
    matches.push([positions[start][0], positions[start + needle.length - 1][1]]);
  }
  return matches;
}

export function highlightPhrase(element, matches) {
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let node, start = 0;
  while ((node = walker.nextNode())) {
    nodes.push({node, start, end: start + node.length});
    start += node.length;
  }
  for (const {node, start, end} of nodes) {
    const overlaps = matches.filter(([a, b]) => a < end && b > start);
    if (!overlaps.length) continue;
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    for (const [a, b] of overlaps) {
      const from = Math.max(a - start, 0), to = Math.min(b - start, node.length);
      fragment.append(document.createTextNode(node.data.slice(cursor, from)));
      const mark = document.createElement('mark');
      mark.className = 'adversary-match';
      mark.textContent = node.data.slice(from, to);
      fragment.append(mark);
      cursor = to;
    }
    fragment.append(document.createTextNode(node.data.slice(cursor)));
    node.replaceWith(fragment);
  }
}

export function clearHighlights(root) {
  root.querySelectorAll('mark.adversary-match').forEach(mark => {
    const parent = mark.parentNode;
    mark.replaceWith(document.createTextNode(mark.textContent));
    parent.normalize();
  });
}
