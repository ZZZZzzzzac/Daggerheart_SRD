"""从 SRD 站装备页删除「战斗轮椅」规则说明文字，保留型号表（与 ParaTranz 对齐）。"""

from pathlib import Path

SITE = Path(r"D:\Fish\TRPG\Daggerheart_SRD\src\pages\core-mechanics\equipment")
MARK = {
    "zh.md": "# 战斗轮椅",
    "en.md": "# Combat Wheelchair",
}
KEEP_PREFIX = ("#", "|")
KEEP_PARA = ("这些轮椅的框架会与角色及其魔法调谐", "These wheelchairs have frames that are attuned")


def clean(path: Path) -> int:
    lines = path.read_text(encoding="utf-8").split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith(MARK[path.name]))
    head, tail = lines[:start + 1], lines[start + 1:]
    kept = []
    for line in tail:
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        if any(stripped.startswith(p) for p in KEEP_PREFIX):
            kept.append(line)
            continue
        if any(stripped.startswith(p) for p in KEEP_PARA):
            kept.append(line)
            continue
    out = head + kept
    # 压掉连续空行
    result = []
    for line in out:
        if line == "" and result and result[-1] == "":
            continue
        result.append(line)
    path.write_text("\n".join(result).rstrip("\n") + "\n", encoding="utf-8")
    return len(tail) - len(kept)


for name in MARK:
    removed = clean(SITE / name)
    print(name, "删除行数:", removed)
