"""
extract_md.py — 从 paratranz JSON 提取 CN.md 和 EN.md
用于手动编辑修复格式后再 build

用法: python scripts/extract_md.py
输出: src/DH-SRD-CN.md 和 src/DH-SRD-EN.md
"""

import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
SRC_JSON = os.path.join(PROJECT_DIR, 'src', 'DH-SRD-1.0-June-26-2025.md.json')

# ── 英文标题修复（从 sync_fixes_to_json.py 移植） ─────

def fix_en_heading(text):
    """对英文原文应用标题层级修复"""
    lines = text.split('\n')
    result = []
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if not m:
            result.append(line)
            continue
        level = len(m.group(1))
        h_text = m.group(2).strip()
        clean = re.sub(r'<[^>]+>', '', h_text).strip()
        clean = re.sub(r'^\*\*|\*\*$', '', clean)

        new_level = level

        if clean in ('ARCANA', 'BLADE', 'BONE', 'CODEX', 'GRACE', 'MIDNIGHT', 'SAGE', 'SPLENDOR', 'VALOR'):
            new_level = 3
        elif clean in ('DOMAIN CARDS', 'CLASS DOMAINS'):
            new_level = 3
        elif re.match(r'^(BARD|DRUID|GUARDIAN|RANGER|ROGUE|SERAPH|SORCERER|WARRIOR|WIZARD)', clean):
            new_level = 3
        elif re.match(r'^(BARD|DRUID|GUARDIAN|RANGER|ROGUE|SERAPH|SORCERER|WARRIOR|WIZARD) SUBCLASSES', clean):
            new_level = 3
        elif clean == 'SUBCLASSES':
            new_level = 3
        elif re.match(r'^(TROUBADOUR|WORDSMITH|WARDEN|GROVE|BULWARK|VENGEANCE|BEASTBOUND|WAYFINDER|NIGHTWALKER|SYNDICATE|ANGELIC|WINGED|ELEMENTAL|PRIMAL|CALL OF THE|SCHOOL OF)', clean, re.IGNORECASE):
            new_level = 4
        elif re.match(r'^SPELLCAST TRAIT', clean):
            new_level = 5
        elif re.match(r'^(FOUNDATION FEATURE|SPECIALIZATION FEATURE|MASTERY FEATURE)', clean):
            new_level = 5
        elif re.match(r'^(CLASS ITEMS|CLASS FEATURE|.*HOPE FEATURE)$', clean):
            new_level = 4
        elif clean in ('BACKGROUND QUESTIONS', 'RELATIONSHIPS'):
            new_level = 4
        elif re.match(r'^BEAST FORM OPTIONS', clean):
            new_level = 3
        elif re.match(r'^TIER \d', clean):
            new_level = 4
        elif clean in ('WEAPON TABLES', 'PHYSICAL WEAPONS', 'MAGICAL WEAPONS', 'ARMOR AND SHIELD TABLE', 'LOOT AND CONSUMABLES TABLE'):
            new_level = 3
        elif clean in ('ANCESTRIES', 'COMMUNITIES'):
            new_level = 2
        elif re.match(r'^(CLANK|DRAKONA|DWARF|FAERIE|FIRBOLG|FUNGRIL|GALAPA|GIANT|GOBLIN|HALFLING|HUMAN|INFERNIS|KATARI|RIBBET|SIMIAH)', clean):
            new_level = 4
        elif re.match(r'^(HIGHBORNE|LOREBORNE|ORDERBORNE|RIDGEBORNE|SEABORNE|SLYBORNE|UNDERBORNE|WANDERBORNE|WILDBORNE)', clean):
            new_level = 4
        elif clean == 'RUNNING A GAME' or clean.startswith('APPENDIX'):
            new_level = 1

        if new_level != level:
            result.append(f"{'#' * new_level} {h_text}")
        else:
            result.append(line)
    return '\n'.join(result)


def clean_item_blocks(text):
    """移除 item( / rules( / ) / | / --- 等卡片格式"""
    lines = text.split('\n')
    cleaned = []
    skip = False
    for line in lines:
        s = line.rstrip()
        if re.match(r'^item\($', s) or re.match(r'^rules\($', s):
            skip = True
            continue
        if skip and re.match(r'^\)$', s):
            skip = False
            continue
        if re.match(r'^[|/]+$', s):
            continue
        if skip and re.match(r'^-+$', s):
            continue
        if re.match(r'^;\s*', s):
            meta = re.sub(r'^;\s*', '', s)
            meta = re.sub(r',', ' ', meta)
            meta = re.sub(r'\s+', ' ', meta).strip()
            meta_clean = re.sub(r'\*\*', '', meta)
            cleaned.append(f'**{meta_clean}**')
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def clean_div_tags(text):
    text = re.sub(r'<div[^>]*>([^<]*)</div>', r'\1', text)
    text = re.sub(r'<div[^>]*>', '', text)
    text = re.sub(r'</div>', '', text)
    return text


# ── 主流程 ──────────────────────────────────────────

def main():
    if not os.path.exists(SRC_JSON):
        print(f"错误: 找不到 {SRC_JSON}")
        sys.exit(1)

    with open(SRC_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取 CN（译文）和 EN（原文）
    cn_parts = []
    en_parts = []
    for entry in data:
        cn_parts.append(entry.get('translation', ''))
        en_parts.append(entry.get('original', ''))

    cn_text = '\n\n'.join(cn_parts)
    en_text = '\n\n'.join(en_parts)

    # 清理 CN
    cn_text = clean_item_blocks(cn_text)
    cn_text = clean_div_tags(cn_text)

    # 清理并修复 EN
    en_text = fix_en_heading(en_text)
    en_text = clean_item_blocks(en_text)
    en_text = clean_div_tags(en_text)

    # 写文件
    cn_path = os.path.join(PROJECT_DIR, 'src', 'DH-SRD-CN.md')
    en_path = os.path.join(PROJECT_DIR, 'src', 'DH-SRD-EN.md')

    with open(cn_path, 'w', encoding='utf-8') as f:
        f.write(cn_text)
    with open(en_path, 'w', encoding='utf-8') as f:
        f.write(en_text)

    cn_lines = cn_text.count('\n') + 1
    en_lines = en_text.count('\n') + 1
    print(f"CN: {cn_path} ({cn_lines} 行)")
    print(f"EN: {en_path} ({en_lines} 行)")
    print("\n编辑这两个文件修正格式，然后运行:")
    print("  python scripts/build_srd.py --md2")


if __name__ == '__main__':
    main()
