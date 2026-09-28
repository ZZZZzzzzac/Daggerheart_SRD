"""将共用渲染核心产生的装备表接入逐条搜索与旧小节跳转。"""
import html
import re

ROOT = 'core-mechanics/equipment'
KINDS = ('primary-weapons', 'secondary-weapons', 'armor', 'items', 'consumables')


def generate(project, prepared_pages, search_records):
    parent = next((p for p in prepared_pages if p['page']['path'] == ROOT), None)
    if parent is None:
        return
    redirects = {'zh': {}, 'en': {}}
    for kind in KINDS:
        path = f'{ROOT}/{kind}'
        source = next((p for p in prepared_pages if p['page']['path'] == path), None)
        if source is None:
            continue
        search_records[:] = [record for record in search_records if record['path'] != path]
        for lang in ('zh', 'en'):
            for heading in source['rendered']['headings'][lang]:
                redirects[lang][heading['anchor']] = path
            markup = source['linked_html'][lang]
            rows = re.findall(r'<tr data-anchor="([^"]+)"[^>]*>([\s\S]*?)</tr>', markup)
            if not rows:
                raise ValueError(f'装备页面没有条目：{path} {lang}')
            for anchor, row in rows:
                cells = re.findall(r'<td\b[^>]*>([\s\S]*?)</td>', row)
                plain = lambda value: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', value))).strip()
                search_records.append({
                    'language': lang, 'path': path, 'pageTitle': source['page']['title'][lang],
                    'heading': plain(cells[0]), 'anchor': anchor, 'body': plain(' '.join(cells[1:])),
                })
    content_path = project / 'content' / ROOT / '_index.md'
    if not content_path.is_file():
        return
    content = content_path.read_text(encoding='utf-8')
    for lang in ('zh', 'en'):
        old_html = parent['linked_html'][lang]
        new_html = old_html
        for anchor, path in redirects[lang].items():
            marker = f' data-equipment-path="{path}"'
            pattern = r'(<h[1-6]\b[^>]*data-anchor="' + re.escape(anchor) + r'"[^>]*)(>)'
            if re.search(pattern, new_html):
                new_html = re.sub(pattern, lambda m: m[1] + marker + m[2], new_html)
            else:
                element_id = f' id="{anchor}"' if lang == 'zh' else ''
                new_html += f'<span data-anchor="{anchor}"{element_id}{marker}></span>'
        content = content.replace(old_html, new_html)
    content_path.write_text(content, encoding='utf-8')
