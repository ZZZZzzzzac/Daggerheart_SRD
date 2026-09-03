"""proxy_server.py 行为测试"""

import sys
import os
import subprocess
import threading
import urllib.request
import urllib.error
import json as json_mod
import pytest
from pathlib import Path
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proxy_server


def test_git_sync_keeps_retrying_until_push_succeeds(monkeypatch, tmp_path):
    attempts = iter([
        subprocess.CompletedProcess(["git", "push"], 1, "", "network down"),
        subprocess.CompletedProcess(["git", "push"], 1, "", "still down"),
        subprocess.CompletedProcess(["git", "push"], 0, "", ""),
    ])
    sleeps = []
    monkeypatch.setattr(proxy_server.subprocess, "run", lambda *args, **kwargs: next(attempts))
    monkeypatch.setattr(proxy_server.time, "sleep", sleeps.append)
    sync = proxy_server.GitSync(tmp_path)
    sync.state = {"status": "pending", "commit": "abc", "updatedAt": "", "error": ""}

    sync._push_with_retry()

    assert sync.snapshot()["status"] == "synced"
    assert sleeps == [3, 15]


# ═══════════════════════════════════════════
# 层 1：路径安全检查
# ═══════════════════════════════════════════

def _setup_fake_project(monkeypatch):
    """对 PROJECT_DIR / PAGES_DIR 做平台兼容的 monkeypatch"""
    proj = Path(os.path.normpath("/fake/project"))
    pages = proj / "src" / "pages"
    monkeypatch.setattr(proxy_server, "PROJECT_DIR", proj)
    monkeypatch.setattr(proxy_server, "PAGES_DIR", pages)
    return proj, pages


def test_resolve_valid_path(monkeypatch):
    """合法 src/pages/ 路径返回完整路径"""
    proj, pages = _setup_fake_project(monkeypatch)

    result = proxy_server._resolve_path("src/pages/intro/zh.md")
    expected = (proj / "src" / "pages" / "intro" / "zh.md").resolve()
    assert result == expected


def test_resolve_block_traversal(monkeypatch):
    """路径遍历攻击被拒绝（.. 越权后不落在 PAGES_DIR 内）"""
    _setup_fake_project(monkeypatch)

    result = proxy_server._resolve_path("src/pages/../../../etc/passwd")
    assert result is None


def test_resolve_block_non_pages(monkeypatch):
    """不以 src/pages/ 开头的路径直接拒绝"""
    _setup_fake_project(monkeypatch)

    result = proxy_server._resolve_path("src/other/file.md")
    assert result is None


# ═══════════════════════════════════════════
# 层 2：文件读写
# ═══════════════════════════════════════════

def _setup_tmp_project(monkeypatch, tmp_path):
    """创建临时项目结构并 monkeypatch PROJECT_DIR / PAGES_DIR"""
    proj = Path(tmp_path)
    pages = proj / "src" / "pages"
    os.makedirs(pages, exist_ok=True)
    monkeypatch.setattr(proxy_server, "PROJECT_DIR", proj)
    monkeypatch.setattr(proxy_server, "PAGES_DIR", pages)
    return proj, pages


def test_read_file_returns_content(monkeypatch, tmp_path):
    """读取已存在的文件返回正确内容"""
    proj, pages = _setup_tmp_project(monkeypatch, tmp_path)
    file_path = os.path.join(pages, "intro", "zh.md")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("## 第一章\n\n欢迎阅读。")

    result = proxy_server.read_file("src/pages/intro/zh.md")
    assert result == "## 第一章\n\n欢迎阅读。"


def test_read_file_missing_returns_none(monkeypatch, tmp_path):
    """读取不存在的文件返回 None"""
    _setup_tmp_project(monkeypatch, tmp_path)

    result = proxy_server.read_file("src/pages/nonexistent/zh.md")
    assert result is None


def test_list_pages_returns_md_files(monkeypatch, tmp_path):
    """页面列表只返回 .md 文件，且路径相对于 PROJECT_DIR"""
    proj, pages = _setup_tmp_project(monkeypatch, tmp_path)
    os.makedirs(os.path.join(pages, "intro"), exist_ok=True)
    os.makedirs(os.path.join(pages, "core"), exist_ok=True)

    # 创建 md 文件和干扰文件
    for d in ["intro", "core"]:
        with open(os.path.join(pages, d, "zh.md"), "w", encoding="utf-8") as f:
            f.write("# title")
        with open(os.path.join(pages, d, "en.md"), "w", encoding="utf-8") as f:
            f.write("# title")
        with open(os.path.join(pages, d, "notes.txt"), "w", encoding="utf-8") as f:
            f.write("not md")

    result = proxy_server.list_pages()
    expected = [
        "src/pages/core/en.md",
        "src/pages/core/zh.md",
        "src/pages/intro/en.md",
        "src/pages/intro/zh.md",
    ]
    assert result == expected


def test_page_catalog_uses_chinese_manifest_titles(monkeypatch, tmp_path):
    proj, pages = _setup_tmp_project(monkeypatch, tmp_path)
    (proj / "data").mkdir(exist_ok=True)
    (pages / "core" / "equipment").mkdir(parents=True)
    (pages / "core" / "equipment" / "zh.md").write_text("# 装备", encoding="utf-8")
    (pages / "core" / "equipment" / "en.md").write_text("# Equipment", encoding="utf-8")
    (proj / "data" / "srd.yaml").write_text(
        'pages:\n  - path: core\n    title: {zh: "核心机制", en: "Core Mechanics"}\n'
        '    subs:\n      - path: core/equipment\n        title: {zh: "装备表格", en: "Equipment Tables"}\n',
        encoding="utf-8",
    )

    assert proxy_server.page_catalog() == [{
        "path": "core/equipment",
        "title": {"zh": "装备表格", "en": "Equipment Tables"},
        "files": {
            "zh": "src/pages/core/equipment/zh.md",
            "en": "src/pages/core/equipment/en.md",
        },
    }]


def test_save_and_build_writes_file(monkeypatch, tmp_path):
    """兼容入口返回新的发布结果"""
    monkeypatch.setattr(proxy_server, "publish_edit", lambda *args: {"message": "保存成功"})
    ok, msg = proxy_server.save_and_build("src/pages/intro/zh.md", "## 新内容")
    assert ok is True
    assert "成功" in msg


def test_save_and_build_rejects_empty(monkeypatch, tmp_path):
    """兼容入口保留可读错误"""
    def reject(*args):
        raise proxy_server.PublishError("内容不能为空")
    monkeypatch.setattr(proxy_server, "publish_edit", reject)
    ok, msg = proxy_server.save_and_build("src/pages/intro/zh.md", "   \n  ")
    assert ok is False
    assert "不能为空" in msg


def test_save_and_build_rejects_bad_path(monkeypatch, tmp_path):
    """保存非法路径 → 返回错误"""
    _setup_tmp_project(monkeypatch, tmp_path)

    ok, msg = proxy_server.save_and_build("src/other/secret.md", "# evil")
    assert ok is False
    assert "只允许" in msg


# ═══════════════════════════════════════════
# 层 3：HTTP 端点集成测试
# ═══════════════════════════════════════════

@pytest.fixture
def test_server(monkeypatch, tmp_path):
    """启动真实 HTTP 测试服务器，返回 base_url"""
    proj = Path(tmp_path)
    pages = proj / "src" / "pages"
    os.makedirs(pages, exist_ok=True)

    monkeypatch.setattr(proxy_server, "PROJECT_DIR", proj)
    monkeypatch.setattr(proxy_server, "PAGES_DIR", pages)

    def fake_publish(changes, display_name):
        if not display_name.strip():
            raise proxy_server.PublishError("编辑者名称不能为空")
        for change in changes:
            if not change["content"].strip():
                raise proxy_server.PublishError("内容不能为空")
            if not change["path"].startswith("src/pages/"):
                raise proxy_server.PublishError("非法路径")
        return {"message": "保存成功", "versions": {}, "gitSync": {"status": "pending"}}
    monkeypatch.setattr(proxy_server, "publish_changes", fake_publish)
    monkeypatch.setattr(proxy_server, "FEEDBACK_STORE", proxy_server.FeedbackStore(tmp_path / "feedback.db"))
    proxy_server.RATE_LIMIT.clear()

    server = HTTPServer(("127.0.0.1", 0), proxy_server.ProxyHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()
    server.server_close()


def _api(base, path, method="GET", body=None):
    """向测试服务器发请求，返回 (status, json_body)"""
    url = base + path
    data = None
    if body is not None:
        data = json_mod.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json_mod.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json_mod.loads(e.read())


def test_api_page_list(test_server):
    """GET /api/page-list 返回 200 和 JSON 文件列表"""
    status, data = _api(test_server, "/api/page-list")
    assert status == 200
    assert isinstance(data.get("pages"), list)


def test_api_get_file_ok(test_server, tmp_path):
    """GET /api/get-file 返回 200 和文件内容"""
    pages = os.path.join(str(tmp_path), "src", "pages", "intro")
    os.makedirs(pages, exist_ok=True)
    with open(os.path.join(pages, "zh.md"), "w", encoding="utf-8") as f:
        f.write("# 标题\n\n正文内容。")

    status, data = _api(test_server, "/api/get-file?path=src/pages/intro/zh.md")
    assert status == 200
    assert data["content"] == "# 标题\n\n正文内容。"
    assert data["version"] == proxy_server.content_version(data["content"])


def test_api_get_file_missing_path(test_server):
    """GET /api/get-file 缺 path 参数返回 400"""
    status, data = _api(test_server, "/api/get-file")
    assert status == 400
    assert "error" in data


def test_api_get_file_not_found(test_server):
    """GET /api/get-file 文件不存在返回 404"""
    status, data = _api(test_server, "/api/get-file?path=src/pages/no/such.md")
    assert status == 404


def test_api_save_ok(test_server):
    """POST /api/save 合法请求返回 200"""
    status, data = _api(test_server, "/api/save", method="POST",
                        body={"path": "src/pages/test/zh.md", "content": "# 测试", "displayName": "测试者"})
    assert status == 200
    assert "成功" in data.get("message", "")


def test_api_save_empty_content(test_server):
    """POST /api/save 空内容返回 400"""
    status, data = _api(test_server, "/api/save", method="POST",
                        body={"path": "src/pages/test/zh.md", "content": "  ", "displayName": "测试者"})
    assert status == 400


def test_api_save_bad_path(test_server):
    """POST /api/save 非法路径返回 400"""
    status, data = _api(test_server, "/api/save", method="POST",
                        body={"path": "src/other/secret.md", "content": "# evil", "displayName": "测试者"})
    assert status == 400


def test_api_preview_endpoint_is_removed(test_server):
    status, data = _api(test_server, "/api/preview", method="POST",
                        body={"content": "## 动作掷骰", "language": "zh"})
    assert status == 404
    assert data["error"] == "Not found"


def test_editor_and_admin_publish_status_endpoints_match(test_server):
    editor_status, editor_data = _api(test_server, "/api/publish-status")
    admin_status, admin_data = _api(test_server, "/api/admin/publish-status")

    assert editor_status == admin_status == 200
    assert editor_data == admin_data


def test_api_feedback_and_admin_workflow(test_server):
    status, created = _api(test_server, "/api/feedback", method="POST", body={
        "message": "这里有错字", "contact": "", "path": "core", "anchor": "roll",
        "language": "zh", "version": "current", "website": "",
    })
    assert status == 201
    status, inbox = _api(test_server, "/api/admin/feedback")
    assert status == 200
    assert inbox["unread"] == 1
    assert inbox["feedback"][0]["message"] == "这里有错字"
    status, updated = _api(test_server, "/api/admin/feedback/update", method="POST", body={
        "id": created["id"], "status": "accepted", "note": "已修正",
    })
    assert status == 200
    assert updated["updated"] is True


def test_api_feedback_rejects_empty_message(test_server):
    status, data = _api(test_server, "/api/feedback", method="POST", body={"message": "", "website": ""})
    assert status == 400
    assert "error" in data
