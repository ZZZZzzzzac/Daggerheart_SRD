"""
附录 EN 重写：从 ZH 提取元数据，在 EN 中匹配卡片名，替换标题和 metadata。
"""
import re, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
SRC = os.path.join(PROJECT_DIR, 'src', 'pages', 'appendix')

DOMAIN_MAP = {"奥术": "Arcana", "利刃": "Blade", "骸骨": "Bone", "典籍": "Codex",
              "优雅": "Grace", "午夜": "Midnight", "贤者": "Sage", "辉耀": "Splendor", "勇气": "Valor"}
TYPE_MAP = {"法术": "Spell", "能力": "Ability", "魔典": "Grimoire"}

with open(SRC + "/zh.md", "r", encoding="utf-8") as f:
    zh = f.read()
with open(SRC + "/en.md", "r", encoding="utf-8") as f:
    en = f.read()

# ===== Step 1: Parse all cards from ZH =====
zh_cards = []
zlines = zh.split("\n")
for i, line in enumerate(zlines):
    m = re.match(r'^####\s+\S+\s+([A-Z][A-Z\'\s]+(?:[-\'][A-Z\'\s]+)*)$', line)
    if not m:
        continue
    en_name = m.group(1).strip()
    # Next line should be **metadata**
    if i + 1 >= len(zlines):
        continue
    meta_match = re.match(r'^\*\*(.+?)\*\*', zlines[i + 1].strip())
    if not meta_match:
        continue
    raw_meta = meta_match.group(1).strip()
    # raw_meta example: "1 级 奥术 法术 回想费用：0"
    # Parse: level, domain_zh, type_zh, recall
    meta_parts = raw_meta.split()
    level = ""
    domain_zh = ""
    type_zh = ""
    recall = ""
    for p in meta_parts:
        if p.isdigit() and not level:
            level = p
        elif "级" in p:
            continue
        elif "回想费用" in p:
            recall = p.split("：")[-1] if "：" in p else ""
        elif p in DOMAIN_MAP:
            domain_zh = p
        elif p in TYPE_MAP:
            type_zh = p

    # Build EN metadata string
    en_meta_parts = []
    if level:
        en_meta_parts.append(f"Level {level}")
    if domain_zh and type_zh:
        en_meta_parts.append(f"{DOMAIN_MAP[domain_zh]} {TYPE_MAP[type_zh]}")
    elif domain_zh:
        en_meta_parts.append(DOMAIN_MAP[domain_zh])
    elif type_zh:
        en_meta_parts.append(TYPE_MAP[type_zh])
    if recall:
        en_meta_parts.append(f"Recall Cost: {recall}")

    zh_cards.append({
        "en_name": en_name,
        "meta": " ".join(en_meta_parts),
    })

print(f"ZH cards parsed: {len(zh_cards)}")

# ===== Step 2: Find and replace each card in EN =====
# Strategy: split EN into lines, iterate, find card name headings,
# replace heading + subsequent metadata headings with our clean version

lines = en.split("\n")
result = []
i = 0
cards_found = 0

# Build a lookup for quickly finding card names
en_name_set = {c["en_name"]: c for c in zh_cards}

while i < len(lines):
    s = lines[i].strip()

    # Check if this line matches any card name
    found_card = None
    for cn in sorted(en_name_set.keys(), key=len, reverse=True):
        esc = re.escape(cn)
        # Use raw strings + concat to avoid f-string {1,6} set issue
        pats = [
            r'^#{1,6}\s+\*\*' + esc + r'\*\*',
            r'^#{1,6}\s+\*\*' + esc + r'\s+',
            r'^#{1,6}\s+' + esc + r'\s*$',
            r'^##\s+' + esc + r'\s*$',
            r'^####\s+' + esc + r'\s*$',
        ]
        for pat in pats:
            if re.match(pat, s):
                found_card = cn
                break
        if found_card:
            break

    if found_card:
        card = en_name_set[found_card]
        cards_found += 1

        # Skip this line and all subsequent metadata/heading lines until we hit description text
        i += 1
        while i < len(lines):
            ns = lines[i].strip()
            if ns == "":
                i += 1
                continue
            if ns.startswith("#"):
                i += 1
                continue
            # Skip residual bold metadata (Level, Recall Cost, etc.)
            if re.match(r'^\*\*(Level\s+\d+|Recall Cost)', ns):
                i += 1
                continue
            break

        # Now write clean card heading
        result.append(f"#### {card['en_name']}")
        if card["meta"]:
            result.append(f"**{card['meta']}**  ")
        else:
            result.append("")

        # Keep the existing description (current line onward until next card)
        # We already positioned i at the first non-heading, non-blank line
        while i < len(lines):
            ns = lines[i].strip()
            # Check if next line starts a new card
            is_next_card = False
            for cn2 in sorted(en_name_set.keys(), key=len, reverse=True):
                esc2 = re.escape(cn2)
                pats = [
                    r'^#{1,6}\s+\*\*' + esc2 + r'\*\*',
                    r'^#{1,6}\s+\*\*' + esc2 + r'\s+',
                    r'^#{1,6}\s+' + esc2 + r'\s*$',
                ]
                for pat in pats:
                    if re.match(pat, ns):
                        is_next_card = True
                        break
                if is_next_card:
                    break
            if is_next_card:
                break
            result.append(lines[i])
            i += 1
        continue

    result.append(lines[i])
    i += 1

output = "\n".join(result)
output = re.sub(r'\n{3,}', '\n\n', output)

with open(SRC + "/en.md", "w", encoding="utf-8") as f:
    f.write(output)

print(f"Cards found & replaced: {cards_found}")
print("Done!")
