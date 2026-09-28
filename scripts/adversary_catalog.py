"""Assemble the existing Markdown chapter into bilingual, filterable cards."""
import html
import re

SOURCE = "adversaries-and-environments/adversary-data"
PATH = SOURCE


def cards_from_html(rendered):
    cards = {}
    for match in re.finditer(r'<article class="stat-card"([^>]*)>([\s\S]*?)</article>', rendered):
        attrs = {key: html.unescape(value) for key, value in re.findall(r'([\w-]+)="([^"]*)"', match[1])}
        key = attrs["data-card-id"]
        if key in cards:
            raise ValueError(f"资料卡 ID 重复: {key}")
        cards[key] = {"attrs": attrs, "html": match[2]}
    return cards


def generate(project, prepared, site_pages, search_records, kind="adversary"):
    source_path = SOURCE if kind == "adversary" else "adversaries-and-environments/environment-data"
    title_zh = "敌人数据" if kind == "adversary" else "环境数据"
    title_en = "Adversaries" if kind == "adversary" else "Environments"
    source = next((p for p in prepared if p["page"]["path"] == source_path), None)
    if source is None:
        return
    rendered = source.get("linked_html", source["rendered"]["html"])
    data = {lang: cards_from_html(rendered[lang]) for lang in ("zh", "en")}
    if not data["zh"]:
        raise ValueError("资料正文没有卡片标记")
    if set(data["en"]) - set(data["zh"]):
        raise ValueError("英文条目缺少对应的中文 ID")
    search_records[:] = [r for r in search_records if r["path"] != source_path]
    groups = {str(tier): [] for tier in range(1, 5)}
    for key, zh in data["zh"].items():
        attrs = zh["attrs"]
        tier = attrs["data-tier"]
        attributes = {"id": f"{kind}-{key}", "data-tier": tier, "data-type": attrs["data-type"], "data-name-zh": attrs["data-name"], "data-name-en": attrs["data-name-en"], "data-difficulty-zh": attrs["data-difficulty"]}
        attr_html = ' '.join(f'{k}="{html.escape(v, quote=True)}"' for k, v in attributes.items())
        plain = html.unescape(re.sub(r'<[^>]+>', '', zh['html']))
        stats = []
        if kind == "environment":
            difficulty = attrs['data-difficulty']
            short = difficulty if difficulty.isdigit() else '特殊'
            stats.append(f'<span title="{html.escape(difficulty, quote=True)}"><small>难</small> {short}</span>')
            role = {'traversal': '险境', 'exploration': '探索', 'event': '事件', 'social': '社交'}[attrs['data-type']]
        else:
            for label, short, pattern in [('难度', '难', r'难度[：:]\s*(\d+)'), ('阈值', '阈', r'阈值[：:]\s*([\d无/—– -]+)'), ('生命点', '命', r'生命点[：:]\s*(\d+)'), ('压力点', '压', r'压力点[：:]\s*(\d+)')]:
                match = re.search(pattern, plain)
                if not match:
                    raise ValueError(f'{key} 缺少{label}')
                stats.append(f'<span title="{label}"><small>{short}</small> {html.escape(match[1].strip())}</span>')
            role = dict(zip('bruiser horde leader minion ranged skulk social solo standard support'.split(), '斗士 集群 头目 杂兵 远程 潜伏 社交 独狼 标准 辅助'.split()))[attrs['data-type']]
        card = [f'<article class="adversary stat-card {kind}-card" {attr_html}><div class="compact-entry"><a class="compact-name" href="#{kind}-{key}"><span class="lang-zh">{html.escape(attrs["data-name"])}</span><span class="lang-en">{html.escape(attrs["data-name-en"])}</span></a><span class="compact-role"><b class="compact-tier">T{tier}</b> <span class="lang-zh">{role}</span><span class="lang-en">{attrs["data-type"].title()}</span></span><div class="compact-stats">{"".join(stats)}</div></div>']
        for lang in ("zh", "en"):
            version = data[lang].get(key, zh)
            body = version["html"]
            body = re.sub(r'(<h3\b[^>]*>)([\s\S]*?)(</h3>)', lambda m: f'{m[1]}<a class="adversary-title" href="#{kind}-{key}">{m[2]}</a>{m[3]}', body, count=1)
            notice = ''
            if lang == "en" and key not in data["en"]:
                body = re.sub(r'\s+(?:id|data-anchor)="[^"]*"', '', body)
                notice = '<p class="adversary-notice">English source unavailable. Chinese rules shown.</p>'
            card.append(f'<div class="lang-{lang} srd-language">{notice}{body}</div>')
            search_records.append({"language": lang, "path": source_path, "pageTitle": title_zh if lang == "zh" else title_en, "heading": attrs["data-name"] if lang == "zh" else attrs["data-name-en"], "anchor": f"{kind}-{key}", "body": html.unescape(re.sub(r'<[^>]+>', ' ', body))})
        card.append('</article>')
        groups[tier].append(''.join(card))
    output = []
    tier_anchors = {str(tier): [] for tier in range(1, 5)}
    # Retain every historical non-card anchor so existing chapter links still resolve.
    for lang in ("zh", "en"):
        outside = re.sub(r'<article class="stat-card"[^>]*>[\s\S]*?</article>', '', rendered[lang])
        anchors = re.findall(r'data-anchor="([^"]+)"', outside)
        legacy_targets = dict(re.findall(r'data-legacy-anchor="([^"]+)" data-target-anchor="([^"]+)"', outside))

        def anchor_span(anchor):
            # 目录重组后仍保留别名目标，让旧链接先归一化再切换语言。
            attrs = f'data-anchor="{anchor}"' + (f' id="{anchor}"' if lang == 'zh' else '')
            if anchor in legacy_targets:
                attrs += f' data-legacy-anchor="{anchor}" data-target-anchor="{legacy_targets[anchor]}"'
            return f'<span {attrs}></span>'

        for heading in source['rendered']['headings'][lang]:
            tier_match = re.match(r'(?:位阶|TIER)\s*([1-4])', heading['title'])
            if tier_match and heading['anchor'] in anchors:
                anchor = heading['anchor']
                tier_anchors[tier_match[1]].append(f'<span class="lang-{lang} srd-language">{anchor_span(anchor)}</span>')
                anchors.remove(anchor)
        output.append(f'<div class="lang-{lang} srd-language legacy-anchors">' + ''.join(anchor_span(anchor) for anchor in anchors) + '</div>')
    for tier, cards in groups.items():
        output.append(f'<section class="adversary-tier-group" data-tier-group="{tier}">{"".join(tier_anchors[tier])}<h2 class="tier-heading"><span class="lang-zh">位阶 {tier}</span><span class="lang-en">Tier {tier}</span><small>{["1", "2–4", "5–7", "8–10"][int(tier)-1]} <span class="lang-zh">级</span><span class="lang-en">level(s)</span></small><span class="tier-count">{len(cards)}</span></h2><div class="adversary-grid">' + '\n'.join(cards) + '</div></section>')
    path = project / "content" / source_path / "index.md"
    path.write_text(f'---\ntitle: "{title_zh}"\ntitle_en: "{title_en}"\ncatalog_kind: "{kind}"\nsrd_path: "' + source_path + '"\nlayout: "adversaries"\n---\n' + '\n'.join(output), encoding="utf-8")
    if kind != "adversary":
        return
    # The old experimental address is an alias, never a second navigation entry.
    alias = project / "content/adversaries"
    alias.mkdir(parents=True, exist_ok=True)
    (alias / "index.md").write_text('---\ntitle: "敌人数据"\nlayout: "adversary-redirect"\n---\n', encoding="utf-8")
