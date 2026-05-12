"""
sync_fixes_to_json.py — 将 markdown 修复同步回 paratranz JSON
对 original (EN) 和 translation (ZH) 分别应用格式修复
输出: DH-SRD-1.0-June-26-2025.md.json.fixed.json
"""

import json
import re
import os
import sys

# 路径
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_JSON = os.path.join(PROJECT_DIR, 'src', 'DH-SRD-1.0-June-26-2025.md.json')
OUTPUT = os.path.join(PROJECT_DIR, 'src', 'DH-SRD-1.0-June-26-2025.md.json.fixed.json')


# ── 通用修复函数 ──────────────────────────────────────

def clean_div_tags(text):
    """移除 <div style=...> 内联样式标签"""
    text = re.sub(r'<div[^>]*>([^<]*)</div>', r'\1', text)
    text = re.sub(r'<div[^>]*>', '', text)
    text = re.sub(r'</div>', '', text)
    return text


def clean_paratranz_tags(text):
    """移除 ((++中文)) 和 ((中文)) 类 paratranz 标记"""
    text = re.sub(r'\(\(\+\+[^)]*\)\)', '', text)
    text = re.sub(r'\(\([^)]*\)\)', '', text)
    return text


def clean_item_blocks(text):
    """移除 item( / rules( / ) / | / --- 等卡片格式冗余"""
    lines = text.split('\n')
    cleaned = []
    skip_line = False
    for line in lines:
        s = line.rstrip()
        if re.match(r'^item\($', s) or re.match(r'^rules\($', s):
            skip_line = True
            continue
        if skip_line and re.match(r'^\)$', s):
            skip_line = False
            continue
        if re.match(r'^[|/]+$', s):
            continue
        if skip_line and re.match(r'^-+$', s):
            continue
        if re.match(r'^.+$', s):
            pass
        # 处理 ; 元数据行
        if re.match(r'^;\s*', s):
            meta = re.sub(r'^;\s*', '', s)
            meta = re.sub(r',', ' ', meta)
            meta = re.sub(r'\s+', ' ', meta).strip()
            # 去掉已有 ** 避免重复，再整体加粗
            meta_clean = re.sub(r'\*\*', '', meta)
            cleaned.append(f'**{meta_clean}**')
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def clean_page_breaks(text):
    """移除 page-break div"""
    return re.sub(r'<div[^>]*page-break[^>]*></div>', '', text)


# ── 中文标题修复规则 ──────────────────────────────────

def fix_zh_heading(text):
    """对中文 translation 应用标题层级修复"""
    lines = text.split('\n')
    result = []
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if not m:
            result.append(line)
            continue
        level = len(m.group(1))
        h_text = m.group(2).strip()
        # 去除 ** 以匹配
        clean = re.sub(r'^\*\*|\*\*$', '', h_text)

        new_level = level  # 默认不变

        # 领域名 → H3
        if clean in ('奥术', '利刃', '骸骨', '典籍', '优雅', '午夜', '贤者', '辉耀', '勇气'):
            new_level = 3
        # 职业领域、领域卡 → H3
        elif clean in ('职业领域', '领域卡'):
            new_level = 3
        # 子职业 → H3
        elif clean in ('子职业',):
            new_level = 3
        # 各职业子职业 → H3
        elif re.match(r'^(吟游诗人|德鲁伊|守护者|游侠|游荡者|神使|术士|战士|法师)子职业$', clean):
            new_level = 3
        # 职业名 → H3
        elif re.match(r'^\*\*?(吟游诗人|德鲁伊|守护者|游侠|游荡者|神使|术士|战士|法师)(?:\*\*|\s+[A-Z])', h_text):
            new_level = 3
        # 种族/社群名 → H4
        elif re.match(r'^\*\*?(械灵|龙人|矮人|精灵|仙灵|羊蹄人|费尔博格|孢菌人|龟人|巨人|哥布林|半身人|人类|魔裔|猫族|兽人|蛙裔|猿族)\*\*?', h_text):
            new_level = 4
        elif re.match(r'^\*\*?(高城之民|博识之民|结社之民|山岭之民|滨海之民|法外之民|地下之民|漂泊之民|荒野之民)\*\*?', h_text):
            new_level = 4
        # 子职业名 (中文+英文大写) → H4
        elif re.match(r'^[一-鿿]{2,8}\s+[A-Z][A-Z\s-]{2,}', clean):
            new_level = 4
        # 施法属性/基础/进阶/精通 → H5
        elif clean in ('施法属性',) or re.match(r'^施法属性[：:]\s*\S+$', clean):
            new_level = 5
        elif clean in ('基础特性', '进阶特性', '精通特性'):
            new_level = 5
        # 职业物品/希望特性/职业特性 → H4
        elif re.match(r'^职业物品$', clean) or re.match(r'^.*的希望特性$', clean) or re.match(r'^职业特性$', clean):
            new_level = 4
        # 背景问题/关系 → H4
        elif clean in ('背景问题', '关系'):
            new_level = 4
        # 野兽形态 → H4/H5
        elif clean in ('野兽形态选项',):
            new_level = 3
        elif re.match(r'^位阶\s*\d', clean):
            new_level = 4
        elif re.match(r'^[一-鿿]+\s+[A-Z]', clean):
            # 子职业名/野兽名等
            if level >= 2:
                new_level = min(level + 1, 6)
        # 游侠相关内容
        elif re.match(r'^游侠伙伴$', clean):
            new_level = 3
        elif re.match(r'^(与你的伙伴合作|使用施法掷骰|让你的伙伴进行攻击|伙伴升级)$', clean):
            new_level = 4
        # 装备表 → H3
        elif clean in ('主武器表', '副武器表', '护甲表', '战利品与消耗品表'):
            new_level = 3
        # 章节名 → H1
        elif clean == '运作一场游戏' or clean == '附录':
            new_level = 1

        if new_level != level:
            result.append(f"{'#' * new_level} {h_text}")
        else:
            result.append(line)
    return '\n'.join(result)


# ── 英文标题修复规则 ──────────────────────────────────

def fix_en_heading(text):
    """对英文 original 应用标题层级修复"""
    lines = text.split('\n')
    result = []
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if not m:
            result.append(line)
            continue
        level = len(m.group(1))
        h_text = m.group(2).strip()
        clean = re.sub(r'<[^>]+>', '', h_text).strip()  # 去掉 <span> 等
        clean = re.sub(r'^\*\*|\*\*$', '', clean)

        new_level = level

        # Domain names → H3
        if clean in ('ARCANA', 'BLADE', 'BONE', 'CODEX', 'GRACE', 'MIDNIGHT', 'SAGE', 'SPLENDOR', 'VALOR'):
            new_level = 3
        elif clean in ('DOMAIN CARDS', 'CLASS DOMAINS'):
            new_level = 3
        # Class names → H3
        elif re.match(r'^(BARD|DRUID|GUARDIAN|RANGER|ROGUE|SERAPH|SORCERER|WARRIOR|WIZARD)', clean):
            new_level = 3
        # Subclass sections → H3
        elif re.match(r'^(BARD|DRUID|GUARDIAN|RANGER|ROGUE|SERAPH|SORCERER|WARRIOR|WIZARD) SUBCLASSES', clean):
            new_level = 3
        # SUBCLASSES intro → H3
        elif clean == 'SUBCLASSES':
            new_level = 3
        # Subclass names → H4
        elif re.match(r'^(TROUBADOUR|WORDSMITH|WARDEN|GROVE|BULWARK|VENGEANCE|BEASTBOUND|WAYFINDER|NIGHTWALKER|SYNDICATE|ANGELIC|WINGED|ELEMENTAL|PRIMAL|CALL OF THE|SCHOOL OF)', clean, re.IGNORECASE):
            new_level = 4
        # Spellcast trait, Foundation, Specialization, Mastery → H5
        elif re.match(r'^SPELLCAST TRAIT', clean):
            new_level = 5
        elif re.match(r'^(FOUNDATION FEATURE|SPECIALIZATION FEATURE|MASTERY FEATURE)', clean):
            new_level = 5
        # Class features → H4
        elif re.match(r'^(CLASS ITEMS|CLASS FEATURE|.*HOPE FEATURE)$', clean):
            new_level = 4
        # BACKGROUND QUESTIONS, RELATIONSHIPS
        elif clean in ('BACKGROUND QUESTIONS', 'RELATIONSHIPS'):
            new_level = 4
        # Beast forms
        elif re.match(r'^BEAST FORM OPTIONS', clean):
            new_level = 3
        elif re.match(r'^TIER \d', clean):
            new_level = 4
        # Equipment tables → H3
        elif clean in ('WEAPON TABLES', 'PHYSICAL WEAPONS', 'MAGICAL WEAPONS', 'ARMOR AND SHIELD TABLE', 'LOOT AND CONSUMABLES TABLE'):
            new_level = 3
        # Ancestries/Communities → H2 (section headers)
        elif clean in ('ANCESTRIES', 'COMMUNITIES'):
            new_level = 2
        elif re.match(r'^(CLANK|DRAKONA|DWARF|FAERIE|FIRBOLG|FUNGRIL|GALAPA|GIANT|GOBLIN|HALFLING|HUMAN|INFERNIS|KATARI|RIBBET|SIMIAH)', clean):
            new_level = 4
        elif re.match(r'^(HIGHBORNE|LOREBORNE|ORDERBORNE|RIDGEBORNE|SEABORNE|SLYBORNE|UNDERBORNE|WANDERBORNE|WILDBORNE)', clean):
            new_level = 4
        # Chapter title
        elif clean == 'RUNNING A GAME' or clean.startswith('APPENDIX'):
            new_level = 1

        if new_level != level:
            result.append(f"{'#' * new_level} {h_text}")
        else:
            result.append(line)
    return '\n'.join(result)


# ── 英语专用清理 ────────────────────────────────────

def apply_en_cleanup(text):
    """对英文原文应用清理"""
    text = clean_item_blocks(text)
    text = clean_div_tags(text)
    text = clean_page_breaks(text)
    return text


def apply_zh_cleanup(text):
    """对中文译文应用清理"""
    text = clean_item_blocks(text)
    text = clean_paratranz_tags(text)
    text = clean_div_tags(text)
    text = clean_page_breaks(text)
    return text


# ── 主流程 ──────────────────────────────────────────

def main():
    if not os.path.exists(SRC_JSON):
        print(f"错误: 找不到 {SRC_JSON}")
        sys.exit(1)

    with open(SRC_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"加载 {len(data)} 个 sections")

    changes_en = 0
    changes_zh = 0

    for i, entry in enumerate(data):
        key = entry['key']

        # 原文 (EN)
        orig = entry.get('original', '')
        orig_fixed = fix_en_heading(orig)
        orig_fixed = apply_en_cleanup(orig_fixed)
        if orig_fixed != orig:
            entry['original'] = orig_fixed
            changes_en += 1

        # 译文 (ZH)
        trans = entry.get('translation', '')
        trans_fixed = fix_zh_heading(trans)
        trans_fixed = apply_zh_cleanup(trans_fixed)
        if trans_fixed != trans:
            entry['translation'] = trans_fixed
            changes_zh += 1

    # 写输出
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"修改: EN {changes_en} 个 section, ZH {changes_zh} 个 section")
    print(f"输出: {OUTPUT}")
    print(f"\n检查无误后复制到 paratranz 项目目录替换原 .md.json 即可上传")


if __name__ == '__main__':
    main()
