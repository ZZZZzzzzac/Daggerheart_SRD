import sys
import zipfile
from pathlib import Path

import yaml

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "scripts"))
import build_srd


def make_project(tmp_path):
    project = Path(tmp_path)
    (project / "data").mkdir()
    (project / "src" / "pages" / "core").mkdir(parents=True)
    manifest = {
        "version": "srd-9.9",
        "pages": [{"path": "core", "title": {"zh": "核心", "en": "Core"}}],
    }
    (project / "data" / "srd.yaml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    (project / "data" / "glossary.md").write_text("# 规则术语表\n", encoding="utf-8")
    (project / "src" / "pages" / "core" / "zh.md").write_text(
        "## 动作掷骰 {#action-roll}\n\n中文正文", encoding="utf-8"
    )
    (project / "src" / "pages" / "core" / "en.md").write_text(
        "## Action Roll {#action-roll}\n\nEnglish body", encoding="utf-8"
    )
    return project


def prepared_page(path, title_zh, title_en, zh_text, en_text):
    return {
        "page": {"path": path, "title": {"zh": title_zh, "en": title_en}},
        "zh_text": zh_text,
        "en_text": en_text,
    }


def test_clean_export_markdown_removes_site_only_markup():
    text = (
        '<span id="section-gear" data-anchor="section-gear"></span>\n\n'
        "## 装备 {#equipment}\n\n"
        '<img src="/SRD/img/domains/arcana.png" class="domain-icon" alt=""> 奥术领域\n\n'
        '<p class="adversary-notice">站点补充：非 SRD 2.0 条目。</p>\n\n'
        "<!-- adversary: bear | BEAR -->\n\n"
        "#### 熊 BEAR {#section-adversary-bear}\n\n"
        "<!-- /adversary -->\n\n"
        "::: no-glossary\n\n"
        "[[!标记文字]]\n\n"
        ":::\n"
    )

    cleaned = build_srd.clean_export_markdown(text)

    for markup in ("{#", "<!--", "<span", "<img", "<p ", "::: "):
        assert markup not in cleaned
    assert "## 装备" in cleaned
    assert "奥术领域" in cleaned
    assert "站点补充：非 SRD 2.0 条目。" in cleaned
    assert "#### 熊 BEAR" in cleaned
    assert "标记文字" in cleaned


def test_clean_export_markdown_keeps_other_containers_and_code_fences():
    text = (
        "::: tip\n\n保留提示\n\n:::\n\n"
        "::: no-glossary\n\n去掉围栏\n\n:::\n\n"
        "```\n::: no-glossary\n:::\n```\n"
    )

    cleaned = build_srd.clean_export_markdown(text)

    assert "::: tip\n\n保留提示\n\n:::" in cleaned
    assert "去掉围栏" in cleaned
    # 围栏内的 ::: no-glossary 原样保留，围栏外的只删配对围栏、保留正文。
    assert cleaned.count("::: no-glossary") == 1
    assert "```\n::: no-glossary\n:::\n```" in cleaned


def test_page_markdown_uses_the_page_title_as_the_only_h1():
    text = "## 装备 {#equipment}\n\n装备正文\n\n# 武器 {#weapons}\n\n武器正文"

    assert build_srd.page_markdown("装备", text) == "# 装备\n\n装备正文\n\n## 武器\n\n武器正文\n"


def test_page_markdown_levels_sections_continuously():
    text = "## 这是什么 {#what-is-this}\n\n正文\n\n#### 细化小节 {#detail}\n\n细则"

    assert build_srd.page_markdown("介绍", text) == "# 介绍\n\n## 这是什么\n\n正文\n\n### 细化小节\n\n细则\n"


def test_page_markdown_keeps_sibling_sections_at_the_same_level():
    # 领域页把 10 个领域写成 ####，再用 ### 开父级小节；同级领域不能被拆成父子。
    text = "#### 奥术\n\nA\n\n#### 利刃\n\nB\n\n### 职业领域\n\nC"

    assert build_srd.page_markdown("领域", text) == (
        "# 领域\n\n### 奥术\n\nA\n\n### 利刃\n\nB\n\n## 职业领域\n\nC\n"
    )


def test_page_markdown_clamps_the_deepest_levels_to_six():
    # 超过 5 个相异层级时最深的几层会并到 ######；本语料每页最多 4 个层级，不会触发。
    text = "\n\n".join(f"{'#' * level} 小节{level}\n\n正文" for level in range(1, 7))

    out = build_srd.page_markdown("深层", text)
    levels = [len(line.split(" ")[0]) for line in out.splitlines() if line.startswith("#")]

    assert levels == [1, 2, 3, 4, 5, 6, 6]


def test_page_markdown_handles_pages_without_headings():
    assert build_srd.page_markdown("附录", "*本节包含额外信息和参考表。*") == (
        "# 附录\n\n*本节包含额外信息和参考表。*\n"
    )


def test_export_archive_layout_readme_and_determinism(tmp_path):
    prepared = [
        prepared_page("introduction", "介绍", "Introduction", "## 这是什么\n\n中文", "## What is this\n\nEnglish"),
        prepared_page("core-resources/classes", "职业", "Classes", "# 刺客\n\n中文", "# ASSASSIN\n\nEnglish"),
    ]

    target = build_srd.generate_markdown_export(
        tmp_path / "static" / "generated", "srd-test", "https://example.test/SRD/", prepared
    )

    assert target == tmp_path / "static" / "generated" / "export" / build_srd.EXPORT_ZIP_NAME
    with zipfile.ZipFile(target) as archive:
        assert archive.namelist() == [
            "Daggerheart-SRD-MD/README.md",
            "Daggerheart-SRD-MD/zh/complete.md",
            "Daggerheart-SRD-MD/zh/chapters/01-introduction.md",
            "Daggerheart-SRD-MD/zh/chapters/02-core-resources-classes.md",
            "Daggerheart-SRD-MD/en/complete.md",
            "Daggerheart-SRD-MD/en/chapters/01-introduction.md",
            "Daggerheart-SRD-MD/en/chapters/02-core-resources-classes.md",
        ]
        assert all(name.isascii() for name in archive.namelist())
        readme = archive.read("Daggerheart-SRD-MD/README.md").decode("utf-8")
        assert "srd-test" in readme
        assert "https://example.test/SRD/" in readme
        assert "© 2025 Critical Role LLC." in readme
        assert "- `01-introduction.md` 介绍" in readme
        assert "- `02-core-resources-classes.md` Classes" in readme
        complete = archive.read("Daggerheart-SRD-MD/zh/complete.md").decode("utf-8")
        assert complete.startswith("# 匕首之心系统参考文档")
        assert complete.index("# 介绍") < complete.index("# 职业")
        assert archive.read("Daggerheart-SRD-MD/zh/chapters/02-core-resources-classes.md").decode(
            "utf-8"
        ) == "# 职业\n\n## 刺客\n\n中文\n"

    first_build = target.read_bytes()
    build_srd.generate_markdown_export(
        tmp_path / "static" / "generated", "srd-test", "https://example.test/SRD/", prepared
    )
    assert target.read_bytes() == first_build


def test_generate_site_packages_every_page_as_markdown(tmp_path):
    project = make_project(tmp_path)

    build_srd.generate_site(project)

    target = project / "static" / "generated" / "export" / build_srd.EXPORT_ZIP_NAME
    with zipfile.ZipFile(target) as archive:
        assert archive.read("Daggerheart-SRD-MD/zh/chapters/01-core.md").decode("utf-8") == (
            "# 核心\n\n## 动作掷骰\n\n中文正文\n"
        )
        assert archive.read("Daggerheart-SRD-MD/en/chapters/01-core.md").decode("utf-8") == (
            "# Core\n\n## Action Roll\n\nEnglish body\n"
        )
        readme = archive.read("Daggerheart-SRD-MD/README.md").decode("utf-8")
        assert "srd-9.9" in readme
        assert build_srd.EXPORT_SITE_URL in readme


def test_export_archive_rewrites_site_absolute_links(tmp_path):
    prepared = [
        prepared_page(
            "campaign-frames",
            "概述",
            "Overview",
            "## 战役框架\n\n- [秽野之息](/SRD/campaign-frames/the-witherwild/)",
            "## Campaign Frames\n\n- [The Witherwild](/SRD/campaign-frames/the-witherwild/)",
        )
    ]

    target = build_srd.generate_markdown_export(
        tmp_path / "static" / "generated", "srd-test", "https://example.test/SRD/", prepared
    )

    with zipfile.ZipFile(target) as archive:
        zh_chapter = archive.read("Daggerheart-SRD-MD/zh/chapters/01-campaign-frames.md").decode("utf-8")
        en_chapter = archive.read("Daggerheart-SRD-MD/en/chapters/01-campaign-frames.md").decode("utf-8")
    assert "[秽野之息](https://example.test/SRD/campaign-frames/the-witherwild/)" in zh_chapter
    assert "[The Witherwild](https://example.test/SRD/campaign-frames/the-witherwild/)" in en_chapter
    assert "](/SRD/" not in zh_chapter + en_chapter


def test_absolutize_export_links_uses_the_configured_path():
    text = "- [a](/docs/foo/) [b](/docs) [c](/other/)"

    assert build_srd.absolutize_export_links(text, "https://example.test/docs/") == (
        "- [a](https://example.test/docs/foo/) [b](https://example.test/docs/) [c](/other/)"
    )
    # 站点部署在根路径时无法区分站内链接，保持原样。
    assert build_srd.absolutize_export_links(text, "https://example.test/") == text


def test_absolutize_export_links_skips_fenced_code():
    text = "```\n- [a](/docs/foo/)\n```\n- [b](/docs/foo/)"

    assert build_srd.absolutize_export_links(text, "https://example.test/docs/") == (
        "```\n- [a](/docs/foo/)\n```\n- [b](https://example.test/docs/foo/)"
    )


def test_reader_template_links_the_export_archive():
    template = (PROJECT_DIR / "layouts" / "_default" / "baseof.html").read_text(encoding="utf-8")
    css = (PROJECT_DIR / "static" / "css" / "site.css").read_text(encoding="utf-8")

    href = '{{ "generated/export/' + build_srd.EXPORT_ZIP_NAME + '" | relURL }}'
    assert f'href="{href}"' in template
    assert f'download="{build_srd.EXPORT_ZIP_NAME}"' in template
    assert ".export-button" in css
