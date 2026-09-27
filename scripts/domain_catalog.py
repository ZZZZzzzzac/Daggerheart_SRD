"""Build the domain catalog from the shared Markdown renderer."""
import html
import re

DOMAINS = dict(zip('arcana blade bone codex grace midnight sage splendor valor'.split(), '奥术 利刃 骸骨 典籍 优雅 午夜 贤者 辉耀 勇气'.split()))


def generate(project, prepared, search_records):
    source = next((p for p in prepared if p['page']['path'] == 'domain-cards'), None)
    if source is None:
        return
    versions = {}
    for lang, text in source['linked_html'].items():
        entries = {}
        for match in re.finditer(r'<article class="domain-card stat-card"([^>]*)>([\s\S]*?)</article>', text):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', match[1]))
            body = match[2]
            heading = re.search(r'<h4[^>]*data-anchor="([^"]+)"[^>]*>([\s\S]*?)</h4>', body)
            entries[heading[1]] = (attrs, body, html.unescape(re.sub(r'<[^>]*>', '', heading[2])))
        versions[lang] = entries
    if set(versions['zh']) != set(versions['en']):
        raise ValueError('领域卡中英文锚点不一致')
    search_records[:] = [r for r in search_records if r['path'] != 'domain-cards']
    groups = {key: [] for key in DOMAINS}
    for key, (attrs, _, name) in versions['zh'].items():
        domain = next(k for k, v in DOMAINS.items() if v == attrs['data-domain'])
        level, recall, kind = attrs['data-level'], attrs['data-recall'], attrs['data-type']
        en_name = versions['en'][key][2]
        card = [f'<article class="adversary stat-card domain-entry" id="domain-{key}" data-tier="{level}" data-group="{domain}" data-type="{domain}" data-card-type="{kind}" data-recall="{recall}"><div class="compact-entry"><a class="compact-name" href="#domain-{key}"><span class="lang-zh">{html.escape(name)}</span><span class="lang-en">{html.escape(en_name)}</span></a><span class="compact-role">Lv{level} · {attrs["data-domain"]}</span><span class="compact-stats">↻ {recall}</span></div>']
        for lang in ('zh', 'en'):
            body = versions[lang][key][1]
            body = re.sub(r'(<h4[^>]*>)([\s\S]*?)(</h4>)', lambda m: m[1] + f'<a class="adversary-title" href="#domain-{key}">' + m[2] + '</a>' + m[3], body, count=1)
            card.append(f'<div class="lang-{lang} srd-language">{body}</div>')
            search_records.append({'path': 'domain-cards', 'language': lang, 'pageTitle': '领域卡' if lang == 'zh' else 'Domain Cards', 'heading': versions[lang][key][2], 'anchor': key, 'body': html.unescape(re.sub(r'<[^>]+>', ' ', body))})
        groups[domain].append(''.join(card) + '</article>')
    output = []
    for domain, cards in groups.items():
        output.append(f'<section class="adversary-tier-group" data-tier-group="{domain}"><h2 class="tier-heading" id="{domain}-domain"><span class="lang-zh">{DOMAINS[domain]}</span><span class="lang-en">{domain.title()}</span><span class="tier-count">{len(cards)}</span></h2><div class="adversary-grid">' + ''.join(cards) + '</div></section>')
    (project / 'content/domain-cards/index.md').write_text('---\ntitle: "领域卡"\ntitle_en: "Domain Cards"\nsrd_path: "domain-cards"\ncatalog_kind: "domain"\nlayout: "adversaries"\n---\n' + ''.join(output), encoding='utf-8')
