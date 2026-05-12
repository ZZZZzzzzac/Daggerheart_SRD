"""
gen_adversary_pages.py — 将 adversaries-and-environments 拆为4个子页面
敌人数据/环境数据从 JSON 重新生成
"""
import os, json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
SRC = os.path.join(PROJECT_DIR, 'src', 'pages', 'adversaries-and-environments')
ADV_JSON = os.path.join(PROJECT_DIR, '..', 'DaggerHeart_CN', 'projects', 'Daggerheart-Core-Rulebook', 'data', 'adversaries.json')
ENV_JSON = os.path.join(PROJECT_DIR, '..', 'DaggerHeart_CN', 'projects', 'Daggerheart-Core-Rulebook', 'data', 'environments.json')

TIER_NAMES = {"1": "**1** 级", "2": "等级 **2–4**", "3": "等级 **5–7**", "4": "等级 **8–10**"}


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ {path}")


# ============================================================
# 1. Split intro sections (keep original text)
# ============================================================
def split_intros():
    zlines = read_file(SRC + "/zh.md")
    elines = read_file(SRC + "/en.md")

    # ZH intros
    write_file(SRC + "/adversary-mechanics/zh.md", "".join(zlines[:153]))
    write_file(SRC + "/environment-mechanics/zh.md", "".join(zlines[2748:2810]))

    # EN intros
    write_file(SRC + "/adversary-mechanics/en.md", "".join(elines[:161]))
    write_file(SRC + "/environment-mechanics/en.md", "".join(elines[2536:2600]))

    print("  Intro sections split OK")


# ============================================================
# 2. Generate adversary data from JSON
# ============================================================
def gen_adversary_zh(entry):
    lines = []
    name = entry.get("名称", "")
    tier = entry.get("位阶", "?")
    atype = entry.get("种类", "")
    desc = entry.get("简介", "")
    motive = entry.get("动机与战术", "") or entry.get("动机与策略", "")
    diff = entry.get("难度", "")
    major = entry.get("重度伤害阈值", "")
    severe = entry.get("严重伤害阈值", "")
    hp = entry.get("生命点", "")
    stress = entry.get("压力点", "")
    atk_hit = entry.get("攻击命中", "")
    atk_wpn = entry.get("攻击武器", "")
    atk_rng = entry.get("攻击范围", "")
    atk_dmg = entry.get("攻击伤害", "")
    atk_type = entry.get("攻击属性", "")
    exp = entry.get("经历", "")
    features = entry.get("特性", [])

    lines.append(f"#### {name}")
    lines.append("")
    lines.append(f"##### *位阶 **{tier}** {atype}*")
    lines.append("")
    if desc:
        lines.append(f"*{desc}*  ")
    if motive:
        lines.append(f"**动机与战术：** {motive}  ")
    stats = []
    if diff:
        stats.append(f"**难度：** {diff}")
    if major and severe:
        stats.append(f"**阈值：** {major}/{severe}")
    if hp:
        stats.append(f"**生命点：** {hp}")
    if stress:
        stats.append(f"**压力点：** {stress}")
    if atk_hit:
        atk_str = f"**攻击：** {atk_hit}"
        if atk_wpn:
            atk_str += f" | **{atk_wpn}：** {atk_rng}"
        if atk_dmg:
            atk_str += f" | {atk_dmg}"
        if atk_type:
            atk_str += f" {atk_type}"
    if stats:
        lines.append(" | ".join(stats) + "  ")
    if atk_hit:
        lines.append(atk_str + "  ")
    if exp:
        lines.append(f"**经历：** {exp}  ")
    if features:
        lines.append("")
        lines.append("#### **特性**")
        lines.append("")
        for f in features:
            fname = f.get("名称", "")
            ftype = f.get("类型", "")
            fdesc = f.get("特性描述", "")
            marker = f"*{fname} - {ftype}：*" if fname else f"*{ftype}：*"
            lines.append(f"- {marker} {fdesc}")
    lines.append("")
    return "\n".join(lines)


def gen_adversary_data():
    with open(ADV_JSON, "r", encoding="utf-8") as f:
        adv = json.load(f)

    by_tier = {}
    for a in adv:
        by_tier.setdefault(a.get("位阶", "0"), []).append(a)

    # ZH
    parts = ["## 按位阶划分的敌人", ""]
    for tier in sorted(by_tier, key=lambda x: int(x)):
        parts.append(f"## 位阶 **{tier}** 敌人（{TIER_NAMES.get(tier, '**' + tier + '** 级')}）")
        parts.append("")
        for entry in by_tier[tier]:
            parts.append(gen_adversary_zh(entry))
    write_file(SRC + "/adversary-data/zh.md", "\n".join(parts))
    print(f"  ZH adversary data: {len(adv)} entries")


# ============================================================
# 3. Generate environment data from JSON
# ============================================================
def gen_env_zh(entry):
    lines = []
    name = entry.get("名称", "")
    tier = entry.get("位阶", "?")
    etype = entry.get("种类", "")
    desc = entry.get("简介", "")
    impulse = entry.get("趋向", "")
    diff = entry.get("难度", "")
    enemies = entry.get("潜在敌人", "")
    features = entry.get("特性", [])

    lines.append(f"#### {name}")
    lines.append("")
    lines.append(f"##### *位阶 **{tier}** {etype}*")
    lines.append("")
    if desc:
        lines.append(f"*{desc}*  ")
    if impulse:
        lines.append(f"**趋向：** {impulse}  ")
    if diff:
        lines.append(f"**难度：** {diff}  ")
    if enemies:
        lines.append(f"**潜在敌人：** {enemies}  ")
    if features:
        lines.append("")
        lines.append("#### **特性**")
        lines.append("")
        for f in features:
            fname = f.get("名称", "")
            ftype = f.get("类型", "")
            fdesc = f.get("特性描述", "")
            fq = f.get("特性问题", "")
            marker = f"*{fname} - {ftype}：*" if fname else f"*{ftype}：*"
            if fq:
                lines.append(f"- {marker} {fdesc}  ")
                lines.append(f"*{fq}*")
            else:
                lines.append(f"- {marker} {fdesc}")
    lines.append("")
    return "\n".join(lines)


def gen_environment_data():
    with open(ENV_JSON, "r", encoding="utf-8") as f:
        env = json.load(f)

    by_tier = {}
    for e in env:
        by_tier.setdefault(e.get("位阶", "0"), []).append(e)

    # ZH
    parts = ["## 按位阶划分的环境", "", "本节包含以下数据块：", ""]
    for tier in sorted(by_tier, key=lambda x: int(x)):
        parts.append(f"## 位阶 **{tier}** 环境（{TIER_NAMES.get(tier, '**' + tier + '** 级')}）")
        parts.append("")
        for entry in by_tier[tier]:
            parts.append(gen_env_zh(entry))
    write_file(SRC + "/environment-data/zh.md", "\n".join(parts))
    print(f"  ZH environment data: {len(env)} entries")


if __name__ == "__main__":
    print("Splitting intros...")
    split_intros()
    print("Generating adversary data...")
    gen_adversary_data()
    print("Generating environment data...")
    gen_environment_data()
    print("Done!")
