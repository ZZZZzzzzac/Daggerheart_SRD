"""Preserve section links when a Markdown page is split into smaller pages."""
import html
import json
import re


def generate(project, prepared_pages):
    mapping = project / 'data/page-redirects.json'
    if not mapping.exists():
        return
    pages = {item['page']['path']: item for item in prepared_pages}
    for source, languages in json.loads(mapping.read_text(encoding='utf-8')).items():
        if source not in pages:
            raise ValueError(f'旧链接来源页不存在：{source}')
        content_dir = project / 'content' / source
        output = content_dir / '_index.md'
        if not output.exists():
            output = content_dir / 'index.md'
        content = output.read_text(encoding='utf-8')
        for lang, redirects in languages.items():
            if lang not in ('zh', 'en'):
                raise ValueError(f'旧链接语言无效：{lang}')
            markup = pages[source]['linked_html'][lang]
            existing = set(re.findall(r'data-anchor="([^"]+)"', markup))
            markers = []
            for old, target in redirects.items():
                path, anchor = target['path'], target['anchor']
                if path not in pages or f'data-anchor="{anchor}"' not in pages[path]['linked_html'][lang]:
                    raise ValueError(f'旧链接目标不存在：{source}#{old} → {path}#{anchor} ({lang})')
                if old in existing:
                    raise ValueError(f'旧链接覆盖当前锚点：{source}#{old} ({lang})')
                attrs = {'data-anchor': old, 'data-page-path': path}
                if lang == 'zh':
                    attrs['id'] = old
                if old != anchor:
                    attrs['data-legacy-anchor'] = old
                attrs['data-target-anchor'] = anchor
                attributes = ' '.join(f'{key}="{html.escape(value, quote=True)}"' for key, value in attrs.items())
                markers.append(f'<span {attributes} aria-hidden="true"></span>')
            content = content.replace(markup, markup + '\n' + '\n'.join(markers), 1)
        output.write_text(content, encoding='utf-8')
