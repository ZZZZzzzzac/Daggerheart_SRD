import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import proxy_server


@pytest.fixture
def workspace_tmpdir():
    with tempfile.TemporaryDirectory(prefix=".codex-test-tmp-", dir=proxy_server.PROJECT_DIR) as directory:
        yield Path(directory)


class FakeSync:
    def __init__(self):
        self.commits = []
    def queue(self, commit):
        self.commits.append(commit)
    def snapshot(self):
        return {"status": "pending" if self.commits else "idle"}


def publication_project(monkeypatch, tmp_path):
    project = Path(tmp_path)
    page = project / "src" / "pages" / "intro" / "zh.md"
    page.parent.mkdir(parents=True)
    page.write_text("# 旧内容", encoding="utf-8")
    (page.parent / "en.md").write_text("# Old", encoding="utf-8")
    public = project / "public"
    public.mkdir()
    (public / "index.html").write_text("old site", encoding="utf-8")
    monkeypatch.setattr(proxy_server, "PROJECT_DIR", project)
    monkeypatch.setattr(proxy_server, "PAGES_DIR", project / "src" / "pages")
    monkeypatch.setattr(proxy_server, "PUBLIC_DIR", public)
    sync = FakeSync()
    monkeypatch.setattr(proxy_server, "GIT_SYNC", sync)

    def copy_candidate(destination):
        shutil.copytree(project / "src", destination / "src")
    monkeypatch.setattr(proxy_server, "_copy_candidate_project", copy_candidate)

    def build_candidate(candidate):
        output = candidate / "public"
        output.mkdir()
        content = (candidate / "src" / "pages" / "intro" / "zh.md").read_text(encoding="utf-8")
        (output / "index.html").write_text(f"built: {content}", encoding="utf-8")
    monkeypatch.setattr(proxy_server, "_run_candidate_build", build_candidate)
    monkeypatch.setattr(proxy_server, "_commit_changes", lambda paths, name: "abc123")
    return project, page, public, sync


def test_publish_builds_candidate_then_replaces_source_and_site(monkeypatch, tmp_path):
    project, page, public, sync = publication_project(monkeypatch, tmp_path)
    version = proxy_server.content_version("# 旧内容")
    result = proxy_server.publish_edit("src/pages/intro/zh.md", "# 新内容", version, "译者")
    assert page.read_text(encoding="utf-8") == "# 新内容"
    assert (public / "index.html").read_text(encoding="utf-8") == "built: # 新内容"
    assert result["commit"] == "abc123"
    assert sync.commits == ["abc123"]


def test_publish_conflict_does_not_change_source(monkeypatch, tmp_path):
    project, page, public, sync = publication_project(monkeypatch, tmp_path)
    with pytest.raises(proxy_server.PublishError) as caught:
        proxy_server.publish_edit("src/pages/intro/zh.md", "# 新内容", "stale", "译者")
    assert caught.value.status == 409
    assert caught.value.details["conflicts"][0]["currentContent"] == "# 旧内容"
    assert page.read_text(encoding="utf-8") == "# 旧内容"
    assert (public / "index.html").read_text(encoding="utf-8") == "old site"


def test_failed_candidate_build_leaves_live_state_unchanged(monkeypatch, tmp_path):
    project, page, public, sync = publication_project(monkeypatch, tmp_path)
    monkeypatch.setattr(proxy_server, "_run_candidate_build", lambda candidate: (_ for _ in ()).throw(proxy_server.PublishError("构建失败")))
    with pytest.raises(proxy_server.PublishError, match="构建失败"):
        proxy_server.publish_edit("src/pages/intro/zh.md", "# 新内容", proxy_server.content_version("# 旧内容"), "译者")
    assert page.read_text(encoding="utf-8") == "# 旧内容"
    assert (public / "index.html").read_text(encoding="utf-8") == "old site"
    assert sync.commits == []


def test_failed_local_commit_rolls_back_source_and_site(monkeypatch, tmp_path):
    project, page, public, sync = publication_project(monkeypatch, tmp_path)
    monkeypatch.setattr(proxy_server, "_commit_changes", lambda paths, name: (_ for _ in ()).throw(proxy_server.PublishError("commit failed")))
    with pytest.raises(proxy_server.PublishError, match="commit failed"):
        proxy_server.publish_edit("src/pages/intro/zh.md", "# 新内容", proxy_server.content_version("# 旧内容"), "译者")
    assert page.read_text(encoding="utf-8") == "# 旧内容"
    assert (public / "index.html").read_text(encoding="utf-8") == "old site"


def test_change_set_publishes_multiple_pages_in_one_commit(monkeypatch, tmp_path):
    project, page, public, sync = publication_project(monkeypatch, tmp_path)
    english = project / "src" / "pages" / "intro" / "en.md"
    committed = []
    monkeypatch.setattr(
        proxy_server,
        "_commit_changes",
        lambda paths, name: committed.append((paths, name)) or "batch123",
        raising=False,
    )

    result = proxy_server.publish_changes([
        {
            "path": "src/pages/intro/zh.md",
            "content": "# 新内容",
            "baseVersion": proxy_server.content_version("# 旧内容"),
        },
        {
            "path": "src/pages/intro/en.md",
            "content": "# New",
            "baseVersion": proxy_server.content_version("# Old"),
        },
    ], "译者")

    assert page.read_text(encoding="utf-8") == "# 新内容"
    assert english.read_text(encoding="utf-8") == "# New"
    assert committed == [(["src/pages/intro/zh.md", "src/pages/intro/en.md"], "译者")]
    assert result["commit"] == "batch123"
    assert sync.commits == ["batch123"]


def test_change_set_rejects_every_page_when_one_version_conflicts(monkeypatch, tmp_path):
    project, page, public, sync = publication_project(monkeypatch, tmp_path)
    english = project / "src" / "pages" / "intro" / "en.md"

    with pytest.raises(proxy_server.PublishError) as caught:
        proxy_server.publish_changes([
            {
                "path": "src/pages/intro/zh.md",
                "content": "# 新内容",
                "baseVersion": proxy_server.content_version("# 旧内容"),
            },
            {
                "path": "src/pages/intro/en.md",
                "content": "# New",
                "baseVersion": "stale",
            },
        ], "译者")

    assert caught.value.status == 409
    assert caught.value.details["conflicts"][0]["path"] == "src/pages/intro/en.md"
    assert page.read_text(encoding="utf-8") == "# 旧内容"
    assert english.read_text(encoding="utf-8") == "# Old"
    assert (public / "index.html").read_text(encoding="utf-8") == "old site"
    assert sync.commits == []


def test_change_set_requires_editor_name(monkeypatch, tmp_path):
    publication_project(monkeypatch, tmp_path)
    with pytest.raises(proxy_server.PublishError, match="编辑者名称"):
        proxy_server.publish_changes([{
            "path": "src/pages/intro/zh.md",
            "content": "# 新内容",
            "baseVersion": proxy_server.content_version("# 旧内容"),
        }], "  ")


def test_feedback_store_create_list_and_update(tmp_path):
    store = proxy_server.FeedbackStore(Path(tmp_path) / "feedback.db")
    feedback_id = store.create({
        "message": "动作掷骰有错字", "contact": "reader@example.com", "path": "core",
        "anchor": "action-roll", "language": "zh", "version": "srd-1.0",
    })
    records = store.list()
    assert records[0]["id"] == feedback_id
    assert records[0]["status"] == "pending"
    assert records[0]["is_read"] == 0
    assert store.update(feedback_id, "accepted", "已修正") is True
    updated = store.list("accepted")[0]
    assert updated["internal_note"] == "已修正"
    assert updated["is_read"] == 1


def test_feedback_store_rejects_unknown_status(tmp_path):
    store = proxy_server.FeedbackStore(Path(tmp_path) / "feedback.db")
    with pytest.raises(ValueError, match="无效状态"):
        store.update(1, "unknown", "")


def test_feedback_rate_limit():
    proxy_server.RATE_LIMIT.clear()
    assert all(proxy_server.allow_feedback("127.0.0.9", limit=2) for _ in range(2))
    assert proxy_server.allow_feedback("127.0.0.9", limit=2) is False


def test_real_publication_updates_full_site_search_and_keeps_feedback_anchor_resolvable(monkeypatch, workspace_tmpdir):
    root_project = Path(proxy_server.PROJECT_DIR)
    candidate = workspace_tmpdir / "candidate"
    candidate.mkdir()
    proxy_server._copy_candidate_project(candidate)
    shutil.copytree(root_project / "scripts", candidate / "scripts")
    shutil.copy2(root_project / "hugo.exe", candidate / "hugo.exe")
    source = candidate / "src" / "pages" / "introduction" / "zh.md"
    original = source.read_text(encoding="utf-8")
    anchor = re.findall(r"\{#([a-zA-Z][\w-]*)\}", original)[-1]
    marker = "端到端发布索引验证标记"

    monkeypatch.setattr(proxy_server, "PROJECT_DIR", candidate)
    monkeypatch.setattr(proxy_server, "PAGES_DIR", candidate / "src" / "pages")
    monkeypatch.setattr(proxy_server, "PUBLIC_DIR", candidate / "public")
    monkeypatch.setattr(proxy_server, "BUILD_SCRIPT", candidate / "scripts" / "build_srd.py")
    monkeypatch.setattr(proxy_server, "GIT_SYNC", FakeSync())
    monkeypatch.setattr(proxy_server, "_commit_changes", lambda paths, name: "integration123")

    result = proxy_server.publish_edit(
        "src/pages/introduction/zh.md",
        f"{original.rstrip()}\n\n{marker}\n",
        proxy_server.content_version(original),
        "集成测试",
    )

    search = json.loads((candidate / "public" / "generated" / "search-index.json").read_text(encoding="utf-8"))
    record = next(item for item in search["records"] if marker in item["body"])
    page_html = (candidate / "public" / "introduction" / "index.html").read_text(encoding="utf-8")

    assert result["commit"] == "integration123"
    assert (candidate / "public" / "index.html").is_file()
    assert record["path"] == "introduction"
    assert record["anchor"] == anchor
    assert f'id="{anchor}"' in page_html
