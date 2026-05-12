"""
build_srd.py — Daggerheart HTML SRD 构建脚本
从 src/pages/ 读取拆好的页面文件，生成 Hugo content 并构建
"""

import os, re, sys, subprocess, yaml, markdown as md_lib
from makeup_copy import apply_makeup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(PROJECT_DIR, 'content')
PAGES_DIR = os.path.join(PROJECT_DIR, 'src', 'pages')
TOC_FILE = os.path.join(PROJECT_DIR, 'page-toc.yaml')


def read_page(path, suffix):
    fp = os.path.join(PAGES_DIR, path, suffix)
    if not os.path.exists(fp):
        return ''
    with open(fp, 'r', encoding='utf-8') as f:
        return f.read().strip()


def md_to_html(text):
    if not text:
        return ''
    return md_lib.markdown(text, extensions=['extra'])


def generate_page(path, title_zh, title_en, cn_text, en_text):
    cn_html = md_to_html(apply_makeup(cn_text))
    en_html = md_to_html(en_text)
    body = f'<div class="lang-zh">\n{cn_html}\n</div>\n<div class="lang-en">\n{en_html}\n</div>'
    content = f"""---
title: "{title_zh}"
weight: 1
---

<h1><span class="lang-zh">{title_zh}</span><span class="lang-en">{title_en}</span></h1>

{body}
"""
    d = os.path.join(CONTENT_DIR, path)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(content)
    return path


def build():
    with open(TOC_FILE, 'r', encoding='utf-8') as f:
        toc = yaml.safe_load(f)

    os.makedirs(CONTENT_DIR, exist_ok=True)

    # 清理旧父页
    for p in toc.get('pages', []):
        if p.get('subs'):
            old = os.path.join(CONTENT_DIR, p['path'], 'index.html')
            if os.path.exists(old):
                os.remove(old)

    # 首页
    print("生成首页...")
    homepage = """---
title: "匕首之心 HTML SRD"
---

<h1><span class="lang-zh">匕首之心 HTML SRD</span><span class="lang-en">Daggerheart HTML SRD</span></h1>

<p><span class="lang-zh"><a href="https://www.daggerheart.com/">匕首之心 (Daggerheart)</a> 是一款由 Darrington Press 出版的桌上角色扮演游戏。这个网站是本游戏的系统参考文档（System Reference Document, SRD），以 HTML 格式供浏览器查阅。</span>
<span class="lang-en"><a href="https://www.daggerheart.com/">Daggerheart</a> is a tabletop roleplaying game published by Darrington Press. This site is a System Reference Document (SRD) for that game, prepared in HTML format for reference in a browser.</span></p>

<h2 id="license"><span class="lang-zh">授权</span><span class="lang-en">License</span></h2>

<p><span class="lang-zh">本文档依据 <a href="https://www.darringtonpress.com/license">Darrington Press 社群游戏授权条款</a>，视为公共游戏内容（Public Game Content）。</span>
<span class="lang-en">This document is considered Public Game Content per the <a href="https://www.darringtonpress.com/license">Darrington Press Community Gaming License</a>.</span></p>

<p><span class="lang-zh">© 2025 Critical Role LLC. 保留所有权利。</span><span class="lang-en">© 2025 Critical Role LLC. All rights reserved.</span></p>

<h2 id="translators"><span class="lang-zh">致谢</span><span class="lang-en">Acknowledgments</span></h2>

<p><span class="lang-zh">感谢以下译者参与本 SRD 的翻译与审校：</span>
<span class="lang-en">Thank you to the following translators for their contributions to this SRD (sorted by contribution):</span></p>

<ul>
<li><span class="lang-zh"><strong>Alzgrey</strong></span><span class="lang-en"><strong>Alzgrey</strong></span></li>
<li><span class="lang-zh"><strong>ZinGer_KyoN</strong></span><span class="lang-en"><strong>ZinGer_KyoN</strong></span></li>
<li><span class="lang-zh"><strong>三得利乌龙茶</strong></span><span class="lang-en"><strong>三得利乌龙茶</strong></span></li>
<li><span class="lang-zh"><strong>浣熊旅記</strong></span><span class="lang-en"><strong>浣熊旅記</strong></span></li>
<li><span class="lang-zh"><strong>里予</strong></span><span class="lang-en"><strong>里予</strong></span></li>
<li><span class="lang-zh"><strong>末楔</strong></span><span class="lang-en"><strong>末楔</strong></span></li>
<li><span class="lang-zh"><strong>一条腿儿</strong></span><span class="lang-en"><strong>一条腿儿</strong></span></li>
</ul>"""
    with open(os.path.join(CONTENT_DIR, '_index.html'), 'w', encoding='utf-8') as f:
        f.write(homepage)

    # 各页面
    print("生成内容页面...")
    for page in toc.get('pages', []):
        zt = page['title']['zh']
        et = page['title']['en']
        subs = page.get('subs')
        if subs:
            for sub in subs:
                sp = sub['path']
                cn = read_page(sp, 'zh.md')
                en = read_page(sp, 'en.md')
                if not cn or not en:
                    print(f"  ⚠ 缺文件: {sp} (CN={bool(cn)} EN={bool(en)})")
                    continue
                print(f"  ✓ {generate_page(sp, sub['title']['zh'], sub['title']['en'], cn, en)}")
        else:
            p = page['path']
            cn = read_page(p, 'zh.md')
            en = read_page(p, 'en.md')
            if not cn or not en:
                print(f"  ⚠ 缺文件: {p} (CN={bool(cn)} EN={bool(en)})")
                continue
            print(f"  ✓ {generate_page(p, zt, et, cn, en)}")

    # Hugo
    print(f"\nHugo 构建...")
    r = subprocess.run(['hugo'], cwd=PROJECT_DIR,
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode == 0:
        print(f"  ✓ 成功")
    else:
        print(f"  ✗ 失败:\n{r.stderr}")


if __name__ == '__main__':
    build()
