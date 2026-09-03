from pathlib import Path

import yaml


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


def test_reader_mobile_header_keeps_menu_brand_and_actions_on_one_row():
    css = (PROJECT_DIR / "static" / "css" / "site.css").read_text(encoding="utf-8")

    mobile_rules = css.split("@media (max-width: 900px)", 1)[1]
    header_rule = mobile_rules.split(".site-header", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: auto minmax(7rem, 1fr) auto" in header_rule


def test_editor_opens_page_from_url_and_keeps_url_in_sync():
    script = (PROJECT_DIR / "static" / "edit" / "editor.js").read_text(encoding="utf-8")

    assert 'new URLSearchParams(location.search).get("path")' in script
    assert "history.replaceState" in script


def test_editor_keeps_session_drafts_and_renders_without_preview_requests():
    script = (PROJECT_DIR / "static" / "edit" / "editor.js").read_text(encoding="utf-8")
    worker = (PROJECT_DIR / "static" / "edit" / "preview-worker.mjs").read_text(encoding="utf-8")

    assert "new Map()" in script
    assert "new Worker" in script
    assert 'request("/SRD/api/preview"' not in script
    assert "pending-count" in script
    assert "const document =" not in script
    assert "sequence" in worker
    assert "sequence, zh, en" in worker


def test_editor_requires_name_in_publish_dialog_and_polls_github_sync():
    html = (PROJECT_DIR / "static" / "edit" / "index.html").read_text(encoding="utf-8")
    script = (PROJECT_DIR / "static" / "edit" / "editor.js").read_text(encoding="utf-8")

    assert 'id="publish-dialog"' in html
    assert 'id="publish-name"' in html
    assert "required" in html.split('id="publish-name"', 1)[1].split(">", 1)[0]
    assert "/SRD/api/publish-status" in script
    assert "已同步至 GitHub" in script


def test_nginx_editor_routes_share_one_auth_realm():
    nginx = (PROJECT_DIR / "scripts" / "nginx_proxy_snippet.conf").read_text(encoding="utf-8")

    assert "/SRD/api/preview" not in nginx
    assert "location = /SRD/api/publish-status" in nginx
    assert nginx.count('auth_basic "DaggerheartEditor";') == 5


def test_publish_dialog_has_centered_panel_and_grouped_actions():
    css = (PROJECT_DIR / "static" / "edit" / "editor.css").read_text(encoding="utf-8")

    dialog_rule = css.split("#publish-dialog", 1)[1].split("}", 1)[0]
    form_rule = css.split(".publish-form {", 1)[1].split("}", 1)[0]
    actions_rule = css.split(".publish-form .form-actions", 1)[1].split("}", 1)[0]
    assert "position: fixed" in dialog_rule
    assert "margin: auto" in dialog_rule
    assert "padding: 0" in dialog_rule
    assert "display: grid" in form_rule
    assert "display: flex" in actions_rule
    assert "justify-content: flex-end" in actions_rule
    assert ".publish-form .secondary-button" in css


def test_tables_wrap_inside_article_width_without_horizontal_scroll():
    css = (PROJECT_DIR / "static" / "css" / "site.css").read_text(encoding="utf-8")

    assert "table-layout: auto" in css
    assert "table-layout: fixed" not in css
    assert "overflow-wrap: anywhere" in css
    assert ".table-scroll" in css
    assert "overflow-x: auto" not in css


def test_domain_cards_are_a_top_level_card_grid():
    manifest = yaml.safe_load((PROJECT_DIR / "data" / "srd.yaml").read_text(encoding="utf-8"))
    css = (PROJECT_DIR / "static" / "css" / "site.css").read_text(encoding="utf-8")

    paths = [page["path"] for page in manifest["pages"]]
    assert "domain-cards" in paths
    assert all(
        child["path"] != "domain-cards"
        for page in manifest["pages"]
        for child in page.get("subs", [])
    )
    assert ".domain-card-grid" in css
    assert ".domain-card" in css


def test_domain_card_metadata_uses_its_markdown_break_without_extra_blank_line():
    css = (PROJECT_DIR / "static" / "css" / "site.css").read_text(encoding="utf-8")

    rule = css.split(".article-body .domain-card > p:first-of-type > strong:first-child", 1)[1].split("}", 1)[0]
    assert "display: block" not in rule
    assert "margin-bottom" not in rule


def test_site_css_and_editor_modules_use_current_cache_version():
    base = (PROJECT_DIR / "layouts" / "_default" / "baseof.html").read_text(encoding="utf-8")
    editor = (PROJECT_DIR / "static" / "edit" / "index.html").read_text(encoding="utf-8")
    editor_script = (PROJECT_DIR / "static" / "edit" / "editor.js").read_text(encoding="utf-8")
    worker = (PROJECT_DIR / "static" / "edit" / "preview-worker.mjs").read_text(encoding="utf-8")

    assert 'css/site.css?v=20260903h' in base
    assert 'css/site.css?v=20260903h' in editor
    assert 'render-core.mjs?v=20260903h' in editor_script
    assert 'render-core.mjs?v=20260903h' in worker


def test_article_tables_are_not_turned_into_blocks():
    css = (PROJECT_DIR / "static" / "css" / "site.css").read_text(encoding="utf-8")

    table_rule = css.split(".article-body table", 1)[1].split("}", 1)[0]
    assert "display: block" not in table_rule
    assert ".table-scroll" in css
