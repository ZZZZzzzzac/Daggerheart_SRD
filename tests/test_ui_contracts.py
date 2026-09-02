from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def test_management_pages_are_explicitly_light():
    editor = (PROJECT_DIR / "static" / "edit" / "index.html").read_text(encoding="utf-8")
    admin = (PROJECT_DIR / "static" / "admin" / "index.html").read_text(encoding="utf-8")

    assert '<html lang="zh-CN" data-theme="light">' in editor
    assert '<html lang="zh-CN" data-theme="light">' in admin


def test_editor_textarea_uses_site_light_palette():
    css = (PROJECT_DIR / "static" / "edit" / "editor.css").read_text(encoding="utf-8")

    assert "#editor-textarea" in css
    assert "background: var(--paper)" in css
    assert "color: var(--ink)" in css


def test_editor_reuses_reader_header_and_contents_tree():
    html = (PROJECT_DIR / "static" / "edit" / "index.html").read_text(encoding="utf-8")

    assert 'class="site-header editor-site-header"' in html
    assert 'class="site-sidebar"' in html
    assert 'id="contents-tree"' in html
    assert 'class="site-main editor-main"' in html
    assert 'id="page-select"' not in html
    assert 'class="header-actions editor-header-actions"' in html


def test_reader_editor_link_carries_current_page_path():
    template = (PROJECT_DIR / "layouts" / "_default" / "baseof.html").read_text(encoding="utf-8")

    assert '?path={{ . | urlquery }}' in template


def test_editor_opens_page_from_url_and_keeps_url_in_sync():
    script = (PROJECT_DIR / "static" / "edit" / "editor.js").read_text(encoding="utf-8")

    assert 'new URLSearchParams(location.search).get("path")' in script
    assert "history.replaceState" in script


def test_article_tables_are_not_turned_into_blocks():
    css = (PROJECT_DIR / "static" / "css" / "site.css").read_text(encoding="utf-8")

    table_rule = css.split(".article-body table", 1)[1].split("}", 1)[0]
    assert "display: block" not in table_rule
    assert ".table-scroll" in css
