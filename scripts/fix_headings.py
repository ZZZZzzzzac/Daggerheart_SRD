"""
fix_headings.py — 修复 DH-SRD-.md.json.md 的标题层级
根据目录结构、上下文推断正确的标题级别。

使用: python scripts/fix_headings.py
输出: DH-SRD-1.0-June-26-2025.md.json.md.fixed.md
"""

import re
import os

INPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                     'DH-SRD-1.0-June-26-2025.md.json.md')
OUTPUT = INPUT + '.fixed.md'

# ── 规则驱动的标题修复 ──────────────────────────────────────

# 已知错误标题列表 (行号从 1 开始, heading_text → 应改为 N 级)
# 格式: (行号范围或正则, 正确级别)
# 这里用文本匹配而不是行号，避免行号漂移

REPLACE_RULES = []

# 辅助：生成替换规则
def rule(pattern, correct_level, flags=0):
    REPLACE_RULES.append((re.compile(pattern, flags), correct_level))

def fix_line(line):
    """对单行应用修复规则，返回修复后的行"""
    m = re.match(r'^(#{1,6})\s+(.+)$', line)
    if not m:
        return line
    current_level = len(m.group(1))
    heading_text = m.group(2).strip()
    # 去除粗体标记以便匹配
    clean_text = re.sub(r'^\*\*|\*\*$', '', heading_text).strip()

    for pattern, correct_level in REPLACE_RULES:
        if pattern.search(clean_text) or pattern.search(heading_text):
            if correct_level != current_level:
                return f"{'#' * correct_level} {heading_text}\n"
            break

    return line


# ── 规则定义 ────────────────────────────────────────────────

# 第1章: 介绍 — 似乎正确，跳过

# 第2章: 创建角色 — 也似乎正确，跳过

# 第3章: 核心资源 ──────────────────────────────────

# 9个领域名 → H3
rule(r'^(奥术|利刃|骸骨|典籍|优雅|午夜|贤者|辉耀|勇气)$', 3)

# 职业领域 → H3 (属于 核心资源 > 领域)
rule(r'^职业领域$', 3)

# 领域卡 → H3 (属于 核心资源 > 领域)
rule(r'^领域卡$', 3)

# 职业名 → H3 (属于H2"职业"的子级)
PROFESSIONS = [
    '吟游诗人', '德鲁伊', '守护者', '游侠', '游荡者',
    '神使', '术士', '战士', '法师'
]
for p in PROFESSIONS:
    # 匹配 "## **吟游诗人**" 或 "## 吟游诗人" 等
    rule(r'^\*\*?' + p + r'(?:\*\*)?(?:\(\(.*\)\))?\s*$', 3)

# 注意: 有些职业名后面有英文名和标记
rule(r'^\*\*?吟游诗人\*\*?\s*\(\(.*\)\)', 3)
rule(r'^\*\*?德鲁伊 DRUID\*\*?\s*\(\(.*\)\)', 3)

# 子职业节标题 → H3
rule(r'^子职业$', 3)

# 各职业的子职业小节 → H3
rule(r'^吟游诗人子职业$', 3)
rule(r'^德鲁伊子职业$', 3)
rule(r'^守护者子职业$', 3)
rule(r'^游侠子职业$', 3)
rule(r'^游荡者子职业$', 3)
rule(r'^神使的子职业$', 3)
rule(r'^术士子职业$', 3)
rule(r'^战士子职业$', 3)
rule(r'^法师子职业$', 3)

# 子职业 → H4
SUBCLASSES_BARD = ['游唱乐手', '言文巧匠']
SUBCLASSES_DRUID = ['元素结社', '复兴结社']
SUBCLASSES_GUARDIAN = ['壁垒守护', '复仇之誓']
SUBCLASSES_RANGER = ['幽暗追猎', '自然守护']
SUBCLASSES_ROGUE = ['暗影之触', '欺诈大师']
SUBCLASSES_SERAPH = ['炽天使', '守护天使']
SUBCLASSES_SORCERER = ['混沌之源', '天命之血']
SUBCLASSES_WARRIOR = ['武器大师', '战场统帅']
SUBCLASSES_WIZARD = ['奥术学者', '元素使']

all_subclasses = (SUBCLASSES_BARD + SUBCLASSES_DRUID + SUBCLASSES_GUARDIAN +
                  SUBCLASSES_RANGER + SUBCLASSES_ROGUE + SUBCLASSES_SERAPH +
                  SUBCLASSES_SORCERER + SUBCLASSES_WARRIOR + SUBCLASSES_WIZARD)

for sc in all_subclasses:
    rule(r'^' + sc + r'(?:\s+[A-Z].*)?$', 4)

# 职业物品 / 希望特性 / 职业特性 → H4
rule(r'^职业物品$', 4)
rule(r'^(?:.*的)?希望特性$', 4)
rule(r'^职业特性$', 4)
rule(r'^施法属性[：:]\s*\S+$', 5)
rule(r'^基础特性$', 5)
rule(r'^进阶特性$', 5)
rule(r'^精通特性$', 5)
rule(r'^背景问题$', 4)
rule(r'^关系$', 4)

# 野兽形态
rule(r'^野兽形态选项$', 3)
rule(r'^位阶\s*\d', 4)
rule(r'^(迅捷斥候|居家伴侣|灵巧食草者|群居捕食者|深洋斥候|追猎蜘蛛)\s+[A-Z].*$', 5)
rule(r'^(甲壳哨兵|强大野兽|健步行者|突袭毒蛇|猛扑捕食者|翔空猛禽)\s+[A-Z].*$', 5)
rule(r'^(巨型捕食者|巨型蜥种|翔空巨禽|深洋捕食者|传奇野兽)\s+[A-Z].*$', 5)
rule(r'^传奇混种生物$', 5)
rule(r'^庞然巨兽\s+[A-Z].*$', 5)

# 种族 → H3 (属于核心资源 > 种族)
rule(r'^种族$', 2)  # 种族本身是H2

# 社群 → H3 (属于核心资源 > 社群)
rule(r'^社群$', 2)  # 社群本身是H2

# 章节标题纠正
rule(r'^运作一场游戏$', 1)    # 应该是章节级 H1
rule(r'^A?附录$', 1)           # 应该是章节级 H1，名称里去 A 前缀

# 第4章: 核心机制 ──────────────────────────────────

# 可选规则
rule(r'^\*\*可选规则[：:].*\*\*$', 3)

# 装备武器等表 → H3
rule(r'^主武器表$', 3)
rule(r'^副武器表$', 3)
rule(r'^护甲表$', 3)
rule(r'^战利品与消耗品表$', 3)

# 第5章: 运作一场游戏 ──────────────────────────────

# 敌人与环境下的内容 → H3 (属于运作一场游戏)
rule(r'^敌人与环境$', 2)   # 本身就是 H2 section
rule(r'^(首领|精英|喽啰|爪牙|随从|援军|盟友|中立生物|环境危害|恶劣环境|陷阱)$', 3)

# 战役框架 → H2 (与敌人与环境同级)
rule(r'^秽野之息战役框架$', 2)
rule(r'^(战役框架|剧情导火索|威胁|喘息时刻|黑暗征兆)$', 3)

# 第6章: 附录 ──────────────────────────────────────
rule(r'^领域卡查阅$', 2)  # 本身就是 H2

# 运作一场游戏内部的错误 H2 标题（应降级）
# 这部分敌人和怪物条目大多是 H2，应改为 H3
campaign_sections = [
    '秽野之息战役框架',
]
# 战役框架名称列表 — 可能还有更多
# 先不做大范围替换，让用户手动修复

# ── 其他全局模式 ──────────────────────────────────

# 子职业名检测: "中文名 ENGLISH_NAME" (英文全大写或首字母大写)
# 后面通常跟有英文描述，出现在 职业 章节内
# 匹配: **坚毅铁卫 STALWART** 或 坚毅铁卫 STALWART
rule(r'^(?:\*\*)?[一-鿿]{2,8}(?:\*\*)?\s+[A-Z][A-Z\s-]{4,40}$', 4)

# 游侠相关内容 → H4
rule(r'^游侠伙伴$', 3)
rule(r'^与你的伙伴合作$', 4)
rule(r'^使用施法掷骰、希望和经历$', 4)
rule(r'^让你的伙伴进行攻击$', 4)
rule(r'^伙伴升级$', 4)

# 被误标为 # 的表格/特殊内容
rule(r'^副武器表$', 3)
rule(r'^护甲表$', 3)
rule(r'^主武器表$', 3)
rule(r'^战利品与消耗品表$', 3)
rule(r'^游玩指南$', 3)
rule(r'^GM指南$', 3)
rule(r'^\*\*可选规则[：:].*\*\*$', 3)

# ── 处理某些特殊格式问题 ──

def fix_special_lines(line):
    """修复某些非标题格式问题"""
    # 修复 "A附录" → "附录"
    if re.match(r'^#{1,6}\s+A附录', line):
        return line.replace('A附录', '附录')

    # 修复 "#### 选择你的武器：**" — 多了一个 * 且可能不是标题
    if re.match(r'^#{1,6}\s+选择你的武器', line):
        return '###### 选择你的武器\n'

    # 修复 "#### 选择你的武器：**" 这行末尾多了**
    if re.match(r'^#{1,6}\s+选择你的武器.*\*\*$', line):
        return line.rstrip('*\n') + '\n'

    # 修复某些 #### 后应该只是普通文本
    if re.match(r'^####\s+\*\*[^*]+\*\*\s*$', line):
        # 这些4级粗体标题可能是正确的格式，保留
        pass

    return line


# ── 主要处理逻辑 ──────────────────────────────────

def main():
    if not os.path.exists(INPUT):
        print(f"错误: 找不到 {INPUT}")
        return

    with open(INPUT, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed = []
    changes = []

    for i, line in enumerate(lines):
        stripped = line.rstrip('\n')

        # 先应用特殊修复
        line = fix_special_lines(line)

        # 再应用标题规则
        new_line = fix_line(line)

        if new_line != line:
            old_level = re.match(r'^(#+)\s', line).group(1)
            new_level = re.match(r'^(#+)\s', new_line).group(1)
            old_count = len(old_level)
            new_count = len(new_level)
            text = re.match(r'^#+\s+(.*?)(?:\n)?$', line).group(1)[:40]
            changes.append(f"  L{i+1:4d}: {'#'*old_count} → {'#'*new_count}  {text}")

        fixed.append(new_line)

    # 写输出
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.writelines(fixed)

    print(f"处理完成。输出: {OUTPUT}")
    print(f"共修改 {len(changes)} 处标题:\n")
    for c in changes:
        print(c)


if __name__ == '__main__':
    main()
