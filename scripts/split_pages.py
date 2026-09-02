"""
split_pages.py — 将 CN.md/EN.md 按页面拆分到 src/pages/
每页生成一个 zh.md 和一个 en.md 文件
"""
import os, re, yaml, sys, shutil, tempfile, uuid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(PROJECT_DIR, 'src')
PAGES_DIR = os.path.join(SRC_DIR, 'pages')
TOC_FILE = os.path.join(PROJECT_DIR, 'data', 'srd.yaml')

CN_FILE = os.path.join(SRC_DIR, 'DH-SRD-CN.md')
EN_FILE = os.path.join(SRC_DIR, 'DH-SRD-EN.md')

CHAPTER_KEYS = ['介绍', '创建角色', '核心资源', '核心机制', '运作一场游戏', '附录']

EN_CHAPTER_MAP = {
    'INTRODUCTION': '介绍',
    'CHARACTER CREATION': '创建角色',
    'CORE MATERIALS': '核心资源',
    'CORE MECHANICS': '核心机制',
    'RUNNING AN ADVENTURE': '运作一场游戏',
    'APPENDIX': '附录',
}

CN_TO_EN_SUB = {
    '领域': 'DOMAINS',
    '职业': 'CLASSES',
    '种族': 'ANCESTRIES',
    '社群': 'COMMUNITIES',
}


def split_chapters(path, use_en_map=False):
    """按 # 标题拆分章节"""
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    chapters = {}
    current_key = None
    buf = []
    for line in text.split('\n'):
        m = re.match(r'^#\s+(.+)$', line.strip())
        if m:
            heading = m.group(1).strip()
            if use_en_map:
                clean = re.sub(r'<[^>]+>', '', heading).strip()
                mapped = EN_CHAPTER_MAP.get(heading) or EN_CHAPTER_MAP.get(clean)
                if mapped:
                    if current_key:
                        chapters[current_key] = '\n'.join(buf)
                    current_key = mapped
                    buf = []
                    continue
            elif heading in CHAPTER_KEYS:
                if current_key:
                    chapters[current_key] = '\n'.join(buf)
                current_key = heading
                buf = []
                continue
        if current_key:
            buf.append(line)
    if current_key:
        chapters[current_key] = '\n'.join(buf)
    return chapters


def split_subsections(text):
    """按 ## 子标题拆分"""
    sections = {}
    current_key = None
    buf = []
    for line in text.split('\n'):
        m = re.match(r'^##\s+(.+)$', line.strip())
        if m:
            if current_key:
                sections[current_key] = '\n'.join(buf)
            current_key = m.group(1).strip()
            buf = []
            continue
        if current_key:
            buf.append(line)
    if current_key:
        sections[current_key] = '\n'.join(buf)
    return sections


def write_page(dirpath, content, suffix):
    os.makedirs(dirpath, exist_ok=True)
    filepath = os.path.join(dirpath, suffix)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    print(f"  ✓ {filepath}")


def main():
    if not os.path.exists(CN_FILE) or not os.path.exists(EN_FILE):
        print("错误: 找不到 CN.md 或 EN.md")
        sys.exit(1)

    with open(TOC_FILE, 'r', encoding='utf-8') as f:
        toc = yaml.safe_load(f)

    cn_ch = split_chapters(CN_FILE)
    en_ch = split_chapters(EN_FILE, use_en_map=True)

    with tempfile.TemporaryDirectory(prefix='srd-import-', dir=SRC_DIR) as temp_dir:
        candidate_pages = os.path.join(temp_dir, 'pages')
        missing = []
        for page in toc.get('pages', []):
            title_zh = page['title']['zh']
            path = page['path']
            page_dir = os.path.join(candidate_pages, path)

            cn_content = cn_ch.get(title_zh, '')
            en_content = en_ch.get(title_zh, '')
            subs = page.get('subs')
            if subs:
                cn_subs = split_subsections(cn_content)
                en_subs = split_subsections(en_content)
                for sub in subs:
                    heading = sub['heading']
                    sub_dir = os.path.join(candidate_pages, sub['path'])
                    cn_sub = cn_subs.get(heading, '')
                    en_sub = en_subs.get(heading, '')
                    if not en_sub:
                        en_key = CN_TO_EN_SUB.get(heading, '')
                        if en_key:
                            en_sub = en_subs.get(en_key, '')
                    if not cn_sub or not en_sub:
                        missing.append(f"{sub['path']} (zh={bool(cn_sub)}, en={bool(en_sub)})")
                        continue
                    write_page(sub_dir, cn_sub, 'zh.md')
                    write_page(sub_dir, en_sub, 'en.md')
            else:
                if not cn_content or not en_content:
                    missing.append(f"{path} (zh={bool(cn_content)}, en={bool(en_content)})")
                    continue
                write_page(page_dir, cn_content, 'zh.md')
                write_page(page_dir, en_content, 'en.md')

        if missing:
            print("错误: 新版本尚未达到双语完整发布条件:", file=sys.stderr)
            for item in missing:
                print(f"  - {item}", file=sys.stderr)
            return 1

        backup = os.path.join(SRC_DIR, f'.pages-backup-{uuid.uuid4().hex}')
        try:
            if os.path.exists(PAGES_DIR):
                os.replace(PAGES_DIR, backup)
            os.replace(candidate_pages, PAGES_DIR)
        except Exception:
            if os.path.exists(backup) and not os.path.exists(PAGES_DIR):
                os.replace(backup, PAGES_DIR)
            raise
        finally:
            if os.path.exists(backup):
                shutil.rmtree(backup)

    print(f"\n完成！新版页面已整体替换到 {PAGES_DIR}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
