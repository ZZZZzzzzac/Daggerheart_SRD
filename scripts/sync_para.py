#!/usr/bin/env python
"""ParaTranz（项目 14448）↔ SRD 站 双向增量同步。

判定依据是**基线**（`projects/SRD2/sync/baseline.json`），不是时间戳：
ParaTranz 的 updatedAt 会被整包导入刷新，不能代表「谁改的」。

对一句在两边都能匹配上、但文本不同的句子：
  - 只有站点那句与基线不同 → 站点改的 → 写回 ParaTranz
  - 只有 ParaTranz 那句与基线不同 → ParaTranz 改的 → 写回站点
  - 两边都与基线不同 → 冲突，记 `sync/conflicts.jsonl` 交人工

只存在于一边的句子（站点表格化、站点补充条目、ParaTranz 独有的段落）
**不自动写**，只计入报告，避免把表格拆成段落或把站点补充内容倒灌 ParaTranz。

用法（本仓库根目录）：
    python scripts/sync_para.py snapshot
    python scripts/sync_para.py check
    python scripts/sync_para.py check --json
    python scripts/sync_para.py apply --to-site
    python scripts/sync_para.py apply --to-para

状态与报告落在 data/para-sync/（baseline.json / conflicts.jsonl / latest.* / logs/）。

退出码：check/apply 为 0 表示干净，1 表示有冲突或待同步，2 表示执行失败。
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]      # 本仓库根
SYNC_DIR = REPO / "data/para-sync"
BASELINE = SYNC_DIR / "baseline.json"
CONFLICTS = SYNC_DIR / "conflicts.jsonl"
LATEST_JSON = SYNC_DIR / "latest.json"
LATEST_MD = SYNC_DIR / "latest.md"
LOG_DIR = SYNC_DIR / "logs"

DEFAULT_SITE = REPO
PARATRANZ_ENV_FALLBACK = Path(r"D:\Fish\TRPG\DaggerHeart_CN\.env")
API = "https://paratranz.cn/api/projects/14448"
FILES = ("3347716", "3409913")

MIN_LEN = 8
RATIO = 0.90          # 句子相似度门槛，低于此值只报告不自动同步
AMBIGUOUS = 0.03      # 最优与次优差距小于此值视为歧义，不自动同步
BLEND_LIMIT = 24          # 一句里允许自动替换的最大字符数，超过就判冲突
LOG_KEEP = 30

ANCHOR = re.compile(r"\{#[^}]*\}")
HTML = re.compile(r"</?[a-zA-Z][^>]*>")
FULL2HALF = str.maketrans("，。；：！？（）【】“”‘’", ",.;:!?()[]\"\"''")
SENT_END = re.compile(r"[。！？!?]")
DIGITS = re.compile(r"\d+")


# ---------------------------------------------------------------- 文本归一化

def normalize(text: str) -> str:
    """与 compare_sources.py 完全一致的归一化，保证两处判定口径相同。"""
    text = ANCHOR.sub("", text or "")
    text = HTML.sub("", text)
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d{1,2}[.)）]\s*", "", text)
    text = text.replace("|", " ")
    text = re.sub(r"[*_`>~]", "", text)
    text = text.translate(FULL2HALF)
    return re.sub(r"\s+", "", text)


def split_units(text: str) -> list[dict]:
    """把一段 Markdown 切成带位置的句子。

    返回 [{raw, norm, line, start, end}]，line 为 1-based 行号，
    start/end 是该句在**原始行**里的字符区间。
    """
    out: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("|") or stripped.startswith("--") \
                or "{{" in stripped or stripped.startswith(":::"):
            continue
        norm_line = normalize(line)
        if not norm_line or not re.search(r"[\u4e00-\u9fff]", norm_line) \
                or re.search(r"\.{4,}", norm_line):
            continue
        start = 0
        for m in SENT_END.finditer(line):
            seg = line[start:m.end()]
            norm_seg = normalize(seg)
            if len(norm_seg) >= MIN_LEN:
                out.append({"raw": seg, "norm": norm_seg, "line": lineno,
                            "start": start, "end": m.end()})
            start = m.end()
    return out


def sig(text: str) -> str:
    """基线里只存归一化文本的短哈希，基线的体积不至于随全文膨胀。"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]


def same_numbers(a: str, b: str) -> bool:
    """骰子/数值必须完全一致，避免把一只敌人的 1d8 匹配到另一只的 3d10+1。"""
    return sorted(DIGITS.findall(a)) == sorted(DIGITS.findall(b))


def blend(old: str, new: str) -> str | None:
    """把 new 相对 old 的最小改动套到 old 上，保留 old 其余部分的原始写法。

    改动总字符数超过 BLEND_LIMIT 时返回 None（交给人工，不自动改写）。
    """
    sm = difflib.SequenceMatcher(None, old, new)
    ops = sm.get_opcodes()
    cost = sum((i2 - i1) + (j2 - j1) for tag, i1, i2, j1, j2 in ops if tag != "equal")
    if cost > BLEND_LIMIT:
        return None
    buf = []
    for tag, i1, i2, j1, j2 in ops:
        buf.append(old[i1:i2] if tag == "equal" else new[j1:j2])
    return "".join(buf)


# ---------------------------------------------------------------- 取数

def para_session() -> requests.Session:
    """token 依次取：环境变量 → 本仓库 .env → DaggerHeart_CN 的 .env。"""
    for candidate in (REPO / ".env", PARATRANZ_ENV_FALLBACK):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
    token = os.getenv("PARATRANZ_TOKEN")
    if not token:
        sys.exit("错误: 未找到 PARATRANZ_TOKEN（环境变量 / 本仓库 .env / DaggerHeart_CN .env）")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    s.headers["User-Agent"] = "DaggerHeart_CN-sync"
    return s


def fetch_para(s: requests.Session) -> dict[str, dict]:
    """key → {id, text, stage, file}，直读线上，不用本地快照。"""
    out: dict[str, dict] = {}
    for fid in FILES:
        r = s.get(f"{API}/files/{fid}/translation", timeout=180)
        r.raise_for_status()
        for row in r.json():
            out[row["key"]] = {
                "id": row["id"],
                "text": row.get("translation") or "",
                "stage": row.get("stage"),
                "file": fid,
            }
    return out


def read_page(path: Path) -> str:
    """原样读页面，保留 CRLF（站点文件是 CRLF，别在同步时改成 LF）。"""
    with path.open(encoding="utf-8", newline="") as fh:
        return fh.read()


def write_page(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def pages_root(site: Path) -> Path:
    """站点仓库根 → 页面目录。只认 src/pages，避开 public/、var/ 等构建副本。"""
    return site / "src/pages"


def load_site(site: Path) -> dict[str, str]:
    """页面相对路径 → 文件全文（仅 src/pages）。"""
    pages: dict[str, str] = {}
    root = pages_root(site)
    if not root.is_dir():
        sys.exit(f"错误: 站点页面目录不存在：{root}")
    for path in sorted(root.rglob("zh.md")):
        rel = str(path.relative_to(root).parent).replace("\\", "/") or "."
        pages[rel] = read_page(path)
    return pages


# ---------------------------------------------------------------- 对齐

def align(para: dict[str, dict], pages: dict[str, str]) -> dict:
    """句子级对齐，返回 identical / rewritten / paraOnly / siteOnly。"""
    para_units: list[dict] = []
    for key, row in para.items():
        for u in split_units(row["text"]):
            para_units.append({**u, "key": key})

    site_units: list[dict] = []
    for page, text in pages.items():
        for u in split_units(text):
            site_units.append({**u, "page": page})

    site_norms = {u["norm"] for u in site_units}
    para_norms = {u["norm"] for u in para_units}

    site_by_head: dict[str, list[dict]] = {}
    for u in site_units:
        site_by_head.setdefault(u["norm"][:2], []).append(u)
    para_by_head: dict[str, list[dict]] = {}
    for u in para_units:
        para_by_head.setdefault(u["norm"][:2], []).append(u)

    def best(unit: dict, index: dict[str, list[dict]], used: set[int]):
        cands: list[tuple[float, dict]] = []
        for cand in index.get(unit["norm"][:2], []):
            if id(cand) in used:
                continue
            if abs(len(cand["norm"]) - len(unit["norm"])) > max(16, len(unit["norm"]) * 0.5):
                continue
            if not same_numbers(unit["norm"], cand["norm"]):
                continue
            ratio = difflib.SequenceMatcher(None, unit["norm"], cand["norm"]).ratio()
            if ratio >= RATIO:
                cands.append((ratio, cand))
        if not cands:
            return None
        cands.sort(key=lambda x: -x[0])
        if len(cands) > 1 and cands[0][0] - cands[1][0] < AMBIGUOUS:
            return None                      # 有歧义：宁可不写，交给人工
        return cands[0]

    identical, rewritten, para_only = [], [], []
    used_site: set[int] = set()
    for u in para_units:
        if u["norm"] in site_norms:
            identical.append(u)
            continue
        hit = best(u, site_by_head, used_site)
        if hit:
            ratio, cand = hit
            used_site.add(id(cand))
            rewritten.append({"key": u["key"], "page": cand["page"], "ratio": round(ratio, 3),
                              "para": u, "site": cand})
        else:
            para_only.append(u)

    site_only = []
    used_para: set[int] = set()
    for u in site_units:
        if u["norm"] in para_norms:
            continue
        if any(id(u) == id(x["site"]) for x in rewritten):
            continue
        hit = best(u, para_by_head, used_para)
        if hit:
            ratio, cand = hit
            used_para.add(id(cand))
            rewritten.append({"key": cand["key"], "page": u["page"], "ratio": round(ratio, 3),
                              "para": cand, "site": u})
        else:
            site_only.append(u)

    return {"identical": identical, "rewritten": rewritten,
            "paraOnly": para_only, "siteOnly": site_only}


# ---------------------------------------------------------------- 基线

def load_baseline() -> dict:
    if BASELINE.is_file():
        return json.loads(BASELINE.read_text(encoding="utf-8"))
    return {"version": 1, "createdAt": None, "para": {}, "site": {}}


def save_baseline(data: dict) -> None:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def advance_baseline(para: dict[str, dict], pages: dict[str, str],
                     result: dict) -> dict:
    """把「两边已经一致」的句子记进基线。只推进一致的句子，冲突/待同步的不动。"""
    base = load_baseline()
    para_norms: dict[str, set[str]] = {}
    for u in result["identical"]:
        para_norms.setdefault(u["key"], set()).add(sig(u["norm"]))
    # identical 只用 norm 判定，页归属要重新扫一遍句子
    site_sets: dict[str, set[str]] = {}
    for page, text in pages.items():
        site_sets[page] = set(base["site"].get(page, []))
    site_index = {sig(u["norm"]) for u in result["identical"]}
    for page, text in pages.items():
        for u in split_units(text):
            h = sig(u["norm"])
            if h in site_index:
                site_sets.setdefault(page, set()).add(h)

    for key, norms in para_norms.items():
        base["para"][key] = sorted(set(base["para"].get(key, [])) | norms)
    for page, norms in site_sets.items():
        base["site"][page] = sorted(norms)
    base["createdAt"] = now()
    save_baseline(base)
    return base


# ---------------------------------------------------------------- 判定

def decide(item: dict, base: dict) -> str:
    in_para = sig(item["para"]["norm"]) in set(base["para"].get(item["key"], []))
    in_site = sig(item["site"]["norm"]) in set(base["site"].get(item["page"], []))
    if in_para and not in_site:
        return "to-para"          # 站点改了，ParaTranz 还是基线值
    if in_site and not in_para:
        return "to-site"          # ParaTranz 改了，站点还是基线值
    return "conflict"             # 两边都不是基线值（或基线缺失，无法判定）


def classify(result: dict, base: dict) -> dict:
    to_site, to_para, conflicts = [], [], []
    for item in result["rewritten"]:
        verdict = decide(item, base)
        if verdict == "to-site":
            to_site.append(item)
        elif verdict == "to-para":
            to_para.append(item)
        else:
            conflicts.append(item)
    return {"toSite": to_site, "toPara": to_para, "conflicts": conflicts}


# ---------------------------------------------------------------- 写回

def patch_text(text: str, line: int, start: int, end: int, replacement: str) -> str:
    lines = text.splitlines(keepends=True)
    idx = line - 1
    raw = lines[idx]
    lines[idx] = raw[:start] + replacement + raw[end:]
    return "".join(lines)


def apply_to_site(site: Path, items: list[dict], commit: bool) -> list[str]:
    """把 ParaTranz 的句子写进站点 md。返回被改动的页面列表。"""
    changed: dict[str, str] = {}
    touched: list[str] = []
    for item in items:
        page = item["page"]
        path = pages_root(site) / page / "zh.md"
        if page not in changed:
            if not path.is_file():
                continue
            changed[page] = read_page(path)
        text = changed[page]
        s = item["site"]
        merged = blend(s["raw"], item["para"]["raw"])
        if merged is None:
            print(f"  ! 跳过（改动过大，需人工）{item['key']} → {page}:{s['line']}")
            continue
        if normalize(merged) != item["para"]["norm"]:
            print(f"  ! 跳过（合并后与 ParaTranz 不一致）{item['key']} → {page}:{s['line']}")
            continue
        changed[page] = patch_text(text, s["line"], s["start"], s["end"], merged)
        touched.append(f"{item['key']} → {page}:{s['line']}")

    for page, text in changed.items():
        path = pages_root(site) / page / "zh.md"
        current = read_page(path)
        if current != text:
            write_page(path, text)

    if changed and commit:
        msg = "sync: 从 ParaTranz 同步 " + str(len(touched)) + " 处修订"
        subprocess.run(["git", "add", "--", "src/pages"], cwd=site, check=False)
        subprocess.run(["git", "commit", "-q", "-m", msg], cwd=site, check=False)
    return touched


def apply_to_para(s: requests.Session, para: dict[str, dict], items: list[dict]) -> list[str]:
    """把站点的句子写回 ParaTranz，走 PUT /strings 保 stage。"""
    per_key: dict[str, list[dict]] = {}
    for item in items:
        per_key.setdefault(item["key"], []).append(item)

    payload = []
    touched: list[str] = []
    for key, group in per_key.items():
        row = para.get(key)
        if not row:
            continue
        text = row["text"]
        lines = text.splitlines(keepends=True)
        # 同一词条内多处改动：按行倒序应用，避免行内偏移失效
        group.sort(key=lambda x: (x["para"]["line"], x["para"]["start"]), reverse=True)
        for item in group:
            p = item["para"]
            merged = blend(p["raw"], item["site"]["raw"])
            if merged is None or normalize(merged) != item["site"]["norm"]:
                print(f"  ! 跳过（改动过大或不收敛）{key}:{p['line']}")
                continue
            lines[p["line"] - 1] = lines[p["line"] - 1][:p["start"]] + merged + lines[p["line"] - 1][p["end"]:]
            touched.append(f"{key}:{p['line']}")
        new_text = "".join(lines)
        if new_text != text:
            payload.append({"id": row["id"], "translation": new_text, "stage": row["stage"]})

    if not payload:
        return touched

    r = s.put(f"{API}/strings", json={"op": "edit", "items": payload}, timeout=180)
    r.raise_for_status()
    drift = []
    for item in payload:
        cur = s.get(f"{API}/strings/{item['id']}", timeout=60).json()
        if cur.get("translation") != item["translation"] or cur.get("stage") != item["stage"]:
            drift.append(item["id"])
    if drift:
        print(f"  ! 回读不一致的 id：{drift}")
    return touched


# ---------------------------------------------------------------- 报告

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_reports(payload: dict) -> None:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    lines = [f"# ParaTranz ↔ SRD 站 同步检查 {payload['generatedAt']}", "",
             "| 项 | 数量 |", "| --- | --- |"]
    for k, v in payload["counts"].items():
        lines.append(f"| {k} | {v} |")
    if payload["conflicts"]:
        lines += ["", "## 冲突（需人工决定）", ""]
        for c in payload["conflicts"]:
            lines += [f"### {c['key']} @ {c['page']}:{c['siteLine']}",
                      f"- ParaTranz：{c['para']}", f"- 站点：{c['site']}", ""]
    if payload["pending"]["toSite"]:
        lines += ["", "## 待写入站点（ParaTranz 更新）", ""]
        for c in payload["pending"]["toSite"]:
            lines.append(f"- {c['key']} @ {c['page']}:{c['siteLine']}：{c['site']} → {c['para']}")
    if payload["pending"]["toPara"]:
        lines += ["", "## 待写入 ParaTranz（站点更新）", ""]
        for c in payload["pending"]["toPara"]:
            lines.append(f"- {c['key']} @ {c['page']}:{c['siteLine']}：{c['para']} → {c['site']}")
    LATEST_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = payload["generatedAt"].replace(":", "").replace("-", "")[:15]
    (LOG_DIR / f"{stamp}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                                           encoding="utf-8")
    logs = sorted(LOG_DIR.glob("*.json"))
    for old in logs[:-LOG_KEEP]:
        old.unlink(missing_ok=True)


def record_conflicts(items: list[dict]) -> None:
    """按 signature 去重追加，避免每次 check 都重复记同一条冲突。"""
    if not items:
        return
    CONFLICTS.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    if CONFLICTS.is_file():
        for line in CONFLICTS.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line)["signature"])
            except (ValueError, KeyError):
                continue
    fresh = [c for c in items if c["signature"] not in seen]
    if not fresh:
        return
    with CONFLICTS.open("a", encoding="utf-8") as fh:
        for c in fresh:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")


def serialize(results: dict) -> dict:
    def slim(item):
        return {
            "key": item["key"],
            "page": item["page"],
            "ratio": item["ratio"],
            "para": item["para"]["raw"].strip(),
            "paraLine": item["para"]["line"],
            "site": item["site"]["raw"].strip(),
            "siteLine": item["site"]["line"],
            "signature": f"{item['key']}|{normalize(item['para']['raw'])[:40]}|{normalize(item['site']['raw'])[:40]}",
        }
    return {
        "toSite": [slim(x) for x in results["toSite"]],
        "toPara": [slim(x) for x in results["toPara"]],
        "conflicts": [slim(x) for x in results["conflicts"]],
    }


# ---------------------------------------------------------------- 命令

def build_payload(para, pages, results, split) -> dict:
    slim = serialize(split)
    return {
        "generatedAt": now(),
        "counts": {
            "一致句子": len(results["identical"]),
            "改写句": len(results["rewritten"]),
            "仅 ParaTranz 有": len(results["paraOnly"]),
            "仅站点有": len(results["siteOnly"]),
            "待写入站点": len(split["toSite"]),
            "待写入 ParaTranz": len(split["toPara"]),
            "冲突": len(split["conflicts"]),
        },
        "pending": {"toSite": slim["toSite"], "toPara": slim["toPara"]},
        "conflicts": slim["conflicts"],
    }


def cmd_snapshot(args) -> int:
    s = para_session()
    para = fetch_para(s)
    pages = load_site(Path(args.site))
    results = align(para, pages)
    base = advance_baseline(para, pages, results)
    split = classify(results, base)
    payload = build_payload(para, pages, results, split)
    write_reports(payload)
    print(json.dumps({"基线已建立": len(base["para"]), "站点页面": len(base["site"]),
                      "冲突": len(split["conflicts"])}, ensure_ascii=False))
    return 0 if not split["conflicts"] else 1


def cmd_check(args) -> int:
    s = para_session()
    para = fetch_para(s)
    pages = load_site(Path(args.site))
    results = align(para, pages)
    base = load_baseline()
    split = classify(results, base)
    payload = build_payload(para, pages, results, split)
    write_reports(payload)
    record_conflicts(payload["conflicts"])
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        c = payload["counts"]
        print(f"一致 {c['一致句子']} / 改写 {c['改写句']} / 冲突 {c['冲突']} / "
              f"待写站点 {c['待写入站点']} / 待写 Para {c['待写入 ParaTranz']}")
        for x in payload["conflicts"][:10]:
            print(f"  冲突 {x['key']} @ {x['page']}:{x['siteLine']}")
    return 0 if not (split["conflicts"] or split["toSite"] or split["toPara"]) else 1


def cmd_apply(args) -> int:
    if not (args.to_site or args.to_para):
        print("错误：需指定 --to-site 或 --to-para")
        return 2
    s = para_session()
    para = fetch_para(s)
    pages = load_site(Path(args.site))
    results = align(para, pages)
    base = load_baseline()
    split = classify(results, base)

    if split["conflicts"] and not args.allow_conflicts:
        print(f"检测到 {len(split['conflicts'])} 处冲突，先人工裁决（或加 --allow-conflicts 只同步无冲突部分）")
        write_reports(build_payload(para, pages, results, split))
        return 1

    if args.to_site:
        touched = apply_to_site(Path(args.site), split["toSite"], commit=not args.no_commit)
        print(f"写入站点 {len(touched)} 处")
        for t in touched:
            print("  ", t)
    if args.to_para:
        touched = apply_to_para(s, para, split["toPara"])
        print(f"写入 ParaTranz {len(touched)} 处")
        for t in touched:
            print("  ", t)

    # 写回后重算一遍并推进基线，让下次 check 从新状态出发
    s2 = para_session()
    para2 = fetch_para(s2)
    pages2 = load_site(Path(args.site))
    results2 = align(para2, pages2)
    base2 = advance_baseline(para2, pages2, results2)
    split2 = classify(results2, base2)
    payload = build_payload(para2, pages2, results2, split2)
    write_reports(payload)
    print(json.dumps(payload["counts"], ensure_ascii=False))
    return 0 if not (split2["conflicts"] or split2["toSite"] or split2["toPara"]) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="ParaTranz ↔ SRD 站 双向增量同步")
    ap.add_argument("--site", default=str(DEFAULT_SITE))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("snapshot", help="把当前两边一致的句子记为基线")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("check", help="只读检查：差异、冲突、待同步")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("apply", help="执行写回")
    p.add_argument("--to-site", action="store_true", help="把 ParaTranz 的改动写进站点")
    p.add_argument("--to-para", action="store_true", help="把站点的改动写回 ParaTranz")
    p.add_argument("--no-commit", action="store_true", help="改站点但不 git commit")
    p.add_argument("--allow-conflicts", action="store_true", help="有冲突时仍同步无冲突部分")
    p.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    try:
        return args.func(args)
    except requests.HTTPError as exc:
        print(f"错误：接口返回 {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
