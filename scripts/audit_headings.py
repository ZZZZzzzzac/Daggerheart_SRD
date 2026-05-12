"""
audit_headings.py — 扫描并修复 CN.md/EN.md 的 # 标题层级
输出: .fixed 文件 + 改动报告
"""

import re
import os

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
CN_FILE = os.path.join(SRC_DIR, 'DH-SRD-CN.md')
EN_FILE = os.path.join(SRC_DIR, 'DH-SRD-EN.md')


# ── 中文标题修复规则 ──────────────────────────────

def fix_zh_line(line):
    m = re.match(r'^(#{1,6})\s+(.+)$', line)
    if not m:
        return line
    level = len(m.group(1))
    h = m.group(2).strip()
    clean = re.sub(r'^\*\*|\*\*$', '', h)

    # 章节级标题 → H1
    if clean in ('介绍', '创建角色', '核心资源', '核心机制', '运作一场游戏', '附录'):
        return f"# {h}\n"

    # 小节标题 → H2
    if clean in ('这是什么？', '基础 《匕首之心》是什么？', '黄金法则', '裁定大于规则',
                 '游戏流程', '玩家守则与最佳实践', '守则', '最佳实践',
                 '核心游戏循环', '聚焦', '回合顺序与动作经济', '行动与动作',
                 '地图、距离与移动', '状态', '休整', '死亡', '附加规则', '升级', '兼职',
                 '装备', '战利品', '消耗品',
                 '介绍', '游戏主持人指南', '游戏主持人实践', '核心游戏主持人机制',
                 '敌人与环境', '附加游戏主持人指导', '秽野之息战役框架',
                 '领域卡查阅',
                 '第一步：选择一个职业与子职业。', '第一步：', '第二步：', '第三步：',
                 '第四步：', '第五步：', '第六步：', '第七步：', '第八步：', '第九步：',
                 ):
        return f"## {h}\n"

    # 领域/职业/种族/社群 → H2（大节）
    if clean in ('领域', '职业', '种族', '社群'):
        return f"## {h}\n"

    # 领域名 → H3（奥术/利刃...）
    if clean in ('奥术', '利刃', '骸骨', '典籍', '优雅', '午夜', '贤者', '辉耀', '勇气'):
        return f"### {h}\n"

    # 职业领域、领域卡、野兽形态选项 → H3
    if clean in ('职业领域', '领域卡', '野兽形态选项'):
        return f"### {h}\n"

    # 配置和宝库、使用限制 → H3
    if clean in ('配置和宝库', '使用限制'):
        return f"### {h}\n"

    # 职业名 → H3（吟游诗人/德鲁伊...）
    if re.match(r'^\*\*?(吟游诗人|德鲁伊|守护者|游侠|游荡者|神使|术士|战士|法师)\*\*?', clean):
        return f"### {h}\n"

    # XXX子职业 → H3
    if re.match(r'^(吟游诗人|德鲁伊|守护者|游侠|游荡者|神使|术士|战士|法师)子职业$', clean):
        return f"### {h}\n"

    # 子职业 → H3
    if clean == '子职业':
        return f"### {h}\n"

    # 种族/社群名 → H4
    if re.match(r'^\*\*?(械灵|龙人|矮人|精灵|仙灵|羊蹄人|费尔博格|孢菌人|龟人|巨人|哥布林|半身人|人类|魔裔|猫族|兽人|蛙裔|猿族)\*\*?', clean):
        return f"#### {h}\n"
    if re.match(r'^\*\*?(高城之民|博识之民|结社之民|山岭之民|滨海之民|法外之民|地下之民|漂泊之民|荒野之民)\*\*?', clean):
        return f"#### {h}\n"

    # 子职业名 (中文+英文大写) → H4
    if re.match(r'^[一-鿿]{2,8}\s+[A-Z][A-Z\s-]{2,}', clean):
        return f"#### {h}\n"
    if re.match(r'^[一-鿿]{2,8}$', clean) and level <= 3:
        # 纯中文名如 "复兴结社" "神兵驭者"
        return f"#### {h}\n"

    # 职业物品/希望特性/职业特性 → H4
    if re.match(r'^职业物品$', clean) or re.match(r'^.*的希望特性$', clean) or re.match(r'^职业特性$', clean):
        return f"#### {h}\n"
    if clean in ('背景问题', '关系'):
        return f"#### {h}\n"

    # 子职业特性 → H5
    if re.match(r'^施法属性', clean):
        return f"##### {h}\n"
    if clean in ('基础特性', '进阶特性', '精通特性'):
        return f"##### {h}\n"

    # 游侠相关内容
    if clean in ('游侠伙伴',):
        return f"### {h}\n"
    if re.match(r'^(与你的伙伴合作|使用施法掷骰|让你的伙伴进行攻击|伙伴升级)$', clean):
        return f"#### {h}\n"

    # 装备表 → H3
    if clean in ('主武器表', '副武器表', '护甲表', '战利品与消耗品表', '物理武器', '魔法武器'):
        return f"### {h}\n"
    if re.match(r'^可选规则', clean):
        return f"### {h}\n"

    # 位阶 → H4
    if re.match(r'^位阶\s*\d', clean):
        return f"#### {h}\n"

    # 种族特性 → H4
    if clean == '种族特性':
        return f"#### {h}\n"

    # 混合种族 → H4
    if clean in ('混合种族', '混合种族 Mixed Ancestries'):
        return f"#### {h}\n"

    return line


# ── 英文标题修复规则 ──────────────────────────────

def fix_en_line(line):
    m = re.match(r'^(#{1,6})\s+(.+)$', line)
    if not m:
        return line
    level = len(m.group(1))
    h = m.group(2).strip()
    clean = re.sub(r'<[^>]+>', '', h).strip()
    clean = re.sub(r'^\*\*|\*\*$', '', clean)
    caps = clean.upper()

    # 章节 → H1
    if caps in ('INTRODUCTION', 'CHARACTER CREATION', 'CORE MATERIALS',
                'CORE MECHANICS', 'RUNNING AN ADVENTURE', 'APPENDIX'):
        return f"# {h}\n"
    if re.match(r'^(INTRODUCTION|CHARACTER CREATION|CORE MATERIALS|CORE MECHANICS|RUNNING AN ADVENTURE|APPENDIX)', caps):
        return f"# {h}\n"

    # 节 → H2
    h2_headers = [
        'WHAT IS THIS?', 'THE BASICS', 'THE GOLDEN RULE', 'RULINGS OVER RULES',
        'DOMAINS', 'CLASSES', 'ANCESTRIES', 'COMMUNITIES',
        'FLOW OF THE GAME', 'CORE GAMEPLAY LOOP', 'THE SPOTLIGHT',
        'TURN ORDER & ACTION ECONOMY', 'MAKING MOVES & TAKING ACTION',
        'COMBAT', 'STRESS', 'ATTACKING', 'MAPS, RANGE & MOVEMENT',
        'CONDITIONS', 'DOWNTIME', 'DEATH', 'ADDITIONAL RULES', 'ADVANCEMENT',
        'MULTI-CLASSING', 'EQUIPMENT', 'LOOT', 'CONSUMABLES',
        'INTRODUCTION', 'GAME MASTER ADVICE', 'GM PRACTICES',
        'CORE GM MECHANICS', 'ADVERSARIES & ENVIRONMENTS',
        'ADDITIONAL GM ADVICE', 'WITHERWILD CAMPAIGN FRAME',
        'DOMAIN CARD REFERENCE',
    ]
    if clean in h2_headers or caps in h2_headers:
        return f"## {h}\n"

    # STEP X → H2
    if re.match(r'^STEP \d', clean):
        return f"## {h}\n"

    # Domain names → H3
    if clean in ('ARCANA', 'BLADE', 'BONE', 'CODEX', 'GRACE', 'MIDNIGHT', 'SAGE', 'SPLENDOR', 'VALOR'):
        return f"### {h}\n"

    if clean in ('THE 9 DOMAINS ARE:', 'CLASS DOMAINS', 'DOMAIN CARDS',
                 'LOADOUT & VAULT', 'USAGE LIMITS', 'BEAST FORM OPTIONS',
                 'SUBCLASSES', 'BACKGROUND QUESTIONS', 'CONNECTIONS'):
        return f"### {h}\n"

    # 职业名 → H3
    if re.match(r'^(BARD|DRUID|GUARDIAN|RANGER|ROGUE|SERAPH|SORCERER|WARRIOR|WIZARD)\b', clean):
        return f"### {h}\n"

    # XXX SUBCLASSES → H3
    if re.match(r'^(BARD|DRUID|GUARDIAN|RANGER|ROGUE|SERAPH|SORCERER|WARRIOR|WIZARD) SUBCLASSES', clean):
        return f"### {h}\n"

    # 子职业名 → H4
    subclass_names = ['TROUBADOUR', 'WORDSMITH', 'WARDEN OF THE', 'GROVE WARDEN',
                      'BULWARK', 'VENGEANCE', 'BEASTBOUND', 'WAYFINDER',
                      'NIGHTWALKER', 'SYNDICATE', 'ANGELIC', 'WINGED SENTINEL',
                      'ELEMENTAL ORIGIN', 'PRIMAL ORIGIN',
                      'CALL OF THE BRAVE', 'CALL OF THE SLAYER',
                      'SCHOOL OF KNOWLEDGE', 'SCHOOL OF WAR',
                      'COMPANION', 'WORKING WITH YOUR COMPANION',
                      'COMPANIONS IN COMBAT', 'COMPANION ADVANCEMENT',
                      ]
    for sn in subclass_names:
        if clean.upper().startswith(sn):
            return f"#### {h}\n"

    # 种族/社群名 → H4
    if re.match(r'^(CLANK|DRAKONA|DWARF|ELVES|FAERIE|FIRBOLG|FUNGRIL|GALAPA|GIANT|GOBLIN|HALFLING|HUMAN|INFERNIS|KATARI|RIBBET|SIMIAH|ORC)', clean):
        return f"#### {h}\n"
    if re.match(r'^(HIGHBORNE|LOREBORNE|ORDERBORNE|RIDGEBORNE|SEABORNE|SLYBORNE|UNDERBORNE|WANDERBORNE|WILDBORNE)', clean):
        return f"#### {h}\n"
    if clean in ('ANCESTRY FEATURES', 'MIXED ANCESTRY', 'ANCESTRY TRAITS'):
        return f"#### {h}\n"

    # CLASS ITEMS / CLASS FEATURE / HOPE FEATURE → H4
    if re.match(r'^(CLASS ITEMS|CLASS FEATURE|.*HOPE FEATURE)$', clean):
        return f"#### {h}\n"

    # SPELLCAST TRAIT → H5
    if re.match(r'^SPELLCAST TRAIT', clean):
        return f"##### {h}\n"

    # FOUNDATION / SPECIALIZATION / MASTERY FEATURE → H5
    if re.match(r'^(FOUNDATION FEATURE|SPECIALIZATION FEATURE|MASTERY FEATURE)', clean):
        return f"##### {h}\n"

    # WEAPON TABLES sections
    if clean in ('WEAPON TABLES', 'PHYSICAL WEAPONS', 'MAGICAL WEAPONS',
                 'ARMOR AND SHIELD TABLE', 'LOOT AND CONSUMABLES TABLE'):
        return f"### {h}\n"

    # TIER → H4
    if re.match(r'^TIER \d', clean):
        return f"#### {h}\n"

    return line


# ── 主流程 ──────────────────────────────────────────

def process_file(filepath, fix_func, lang_label):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    changes = []
    fixed = []
    for i, line in enumerate(lines):
        stripped = line.rstrip('\n')
        m = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if m:
            old_level = len(m.group(1))
            new_line = fix_func(stripped)
            new_m = re.match(r'^(#{1,6})\s+(.+)$', new_line)
            if new_m:
                new_level = len(new_m.group(1))
                if new_level != old_level:
                    text = new_m.group(2)[:50]
                    changes.append(f"  L{i+1}: {'#'*old_level}→{'#'*new_level}  {text}")
            fixed.append(new_line + '\n')
        else:
            fixed.append(line)

    outpath = filepath + '.fixed'
    with open(outpath, 'w', encoding='utf-8') as f:
        f.writelines(fixed)

    print(f"\n{'='*50}")
    print(f"{lang_label}: {filepath}")
    print(f"共修改 {len(changes)} 处标题\n")
    for c in changes:
        print(c)

    return changes


def main():
    cn_changes = process_file(CN_FILE, fix_zh_line, '中文')
    en_changes = process_file(EN_FILE, fix_en_line, '英文')

    print(f"\n{'='*50}")
    print(f"总计: 中文 {len(cn_changes)} 处, 英文 {len(en_changes)} 处")


if __name__ == '__main__':
    main()
