"""
align_en_headings.py — 从原始 en.md 提取对应子页的 EN 内容，对齐 ZH 标题层级
"""
import re, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
SRC = os.path.join(PROJECT_DIR, 'src', 'pages', 'adversaries-and-environments')
ORIG_EN = SRC + "/en.md"


def fix_adversary_mechanics():
    """敌人机制介绍: EN 已复制，只需修标题"""
    pass  # Already done manually above


def fix_adversary_data():
    """敌人数据: 从原始 en.md 提取 EN (indices 162-2535)，对齐层级"""
    with open(ORIG_EN, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Extract lines 162-2535 (1-indexed: 162..2535)
    section = lines[161:2535]

    # First pass: identify entry heading patterns
    # ZH format: #### EntryName / ##### *Tier X* / #### **特性**
    # EN original has mixed levels for entry names and tier lines

    result = []
    for i, l in enumerate(section):
        stripped = l.strip()
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if not m:
            result.append(l)
            continue

        level = len(m.group(1))
        content = m.group(2)

        # Stay same:
        # ## ADVERSARIES BY TIER
        # #### **TIER X (LEVELS Y-Z)**
        if re.match(r'^## ADVERSARIES BY TIER$', stripped):
            result.append(l)
        elif re.match(r'^#### \*\*TIER \d', stripped):
            result.append(l)

        # ## TIER X ADVERSARIES (...)  →  ## TIER X ADVERSARIES (...)
        elif re.match(r'^#{1,4} TIER \d+ ADVERSARIES', stripped):
            result.append('## ' + content + '\n')

        # #### *Tier ...*  →  ##### *Tier ...*
        elif re.match(r'^#{1,4} \*Tier ', stripped):
            result.append('##### ' + content + '\n')

        # ### or ## ENTRY NAME followed next by a #### *Tier...* line
        # Check next non-blank line
        else:
            # Check if next non-blank line is a tier marker
            next_content = ""
            for j in range(i + 1, min(i + 5, len(section))):
                ns = section[j].strip()
                if ns and not ns.startswith('#'):
                    continue
                if ns:
                    next_content = ns
                    break

            if re.match(r'^#{1,4} \*Tier ', next_content):
                # This is an entry name — convert to ####
                result.append('#### ' + content + '\n')
            elif re.match(r'^#{1,4} \*\*FEATURES', stripped):
                # FEATURES header
                features_level = '####'
                result.append(features_level + ' ' + content + '\n')
            elif re.match(r'^#{1,4} \*\*FEATURES\*\*', stripped):
                result.append('#### ' + content + '\n')
            elif re.match(r'^### \*\*FEATURES\*\*', stripped):
                result.append('#### ' + content + '\n')
            elif re.match(r'^### \*Tier ', stripped):
                result.append('##### ' + content + '\n')
            else:
                # Default: keep as-is but cap at ####
                if level > 4:
                    result.append('#### ' + content + '\n')
                else:
                    result.append(l)

    out = ''.join(result)
    with open(SRC + "/adversary-data/en.md", "w", encoding="utf-8") as f:
        f.write(out)
    print(f"adversary-data/en.md written ({len(section)} lines)")


def fix_environment_mechanics():
    """环境机制介绍: EN 已复制，只需修标题"""
    with open(SRC + "/environment-mechanics/en.md", "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 环境机制介绍 ZH headings are all ## or ####
    # Need to fix: 环境数据模块 改为 ENVIRONMENT STAT BLOCK (not plural)
    changes = {}
    new_lines = []
    for l in lines:
        stripped = l.strip()
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m:
            key = stripped
            if key == '## ENVIRONMENT STAT BLOCKS':
                new_lines.append('## ENVIRONMENT STAT BLOCK\n')
            else:
                new_lines.append(l)
        else:
            new_lines.append(l)

    with open(SRC + "/environment-mechanics/en.md", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("environment-mechanics/en.md updated")


def fix_environment_data():
    """环境数据: 从原始 en.md 提取 EN (indices 2600-3199)，对齐层级"""
    with open(ORIG_EN, "r", encoding="utf-8") as f:
        lines = f.readlines()

    section = lines[2599:]  # From ## ENVIRONMENT STAT BLOCKS BY TIER

    result = []
    for i, l in enumerate(section):
        stripped = l.strip()
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if not m:
            result.append(l)
            continue

        level = len(m.group(1))
        content = m.group(2)

        if re.match(r'^## ENVIRONMENT STAT BLOCKS BY TIER$', stripped):
            result.append(l)
        elif re.match(r'^#### \*\*TIER \d', stripped):
            result.append(l)
        elif re.match(r'^#{1,4} TIER \d+ ENVIRONMENTS$', stripped):
            result.append('## ' + content + '\n')
        elif re.match(r'^#{1,4} \*Tier ', stripped):
            result.append('##### ' + content + '\n')
        elif re.match(r'^#{1,4} \*\*FEATURES', stripped):
            result.append('#### ' + content + '\n')
        elif re.match(r'^### \*\*FEATURES\*\*', stripped):
            result.append('#### ' + content + '\n')
        else:
            # Check if entry name (next non-blank is a tier line or FEATURES)
            next_content = ""
            for j in range(i + 1, min(i + 5, len(section))):
                ns = section[j].strip()
                if ns and not ns.startswith('#'):
                    continue
                if ns:
                    next_content = ns
                    break
            if re.match(r'^#{1,4} \*Tier ', next_content):
                result.append('#### ' + content + '\n')
            else:
                result.append(l)

    out = ''.join(result)
    with open(SRC + "/environment-data/en.md", "w", encoding="utf-8") as f:
        f.write(out)
    print(f"environment-data/en.md written ({len(section)} lines)")


if __name__ == "__main__":
    print("Fixing adversary-mechanics...")
    # Already done above
    print("Fixing adversary-data...")
    fix_adversary_data()
    print("Fixing environment-mechanics...")
    fix_environment_mechanics()
    print("Fixing environment-data...")
    fix_environment_data()
    print("Done!")
