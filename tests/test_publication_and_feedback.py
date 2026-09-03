import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import proxy_server


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
        "anchor": "action-roll", "language": "zh", "version": "current",
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


def test_real_candidate_project_can_complete_full_build(tmp_path):
    candidate = Path(tmp_path) / "candidate"
    candidate.mkdir()
    proxy_server._copy_candidate_project(candidate)
    proxy_server._run_candidate_build(candidate)
    assert (candidate / "public" / "index.html").is_file()
    assert (candidate / "public" / "generated" / "search-index.json").is_file()
