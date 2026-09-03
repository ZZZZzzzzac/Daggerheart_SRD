"""Local editor, atomic publisher, and feedback inbox for the SRD site."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
PAGES_DIR = PROJECT_DIR / "src" / "pages"
BUILD_SCRIPT = SCRIPT_DIR / "build_srd.py"
PUBLIC_DIR = PROJECT_DIR / "public"
VAR_DIR = PROJECT_DIR / "var"
FEEDBACK_DB = Path(os.environ.get("FEEDBACK_DB", VAR_DIR / "feedback.db"))
LISTEN_HOST = os.environ.get("PROXY_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("PROXY_PORT", "5000"))
MAX_JSON_BYTES = 1_000_000
PUBLISH_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def content_version(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def list_pages() -> list[str]:
    pages = []
    pages_dir = Path(PAGES_DIR)
    project_dir = Path(PROJECT_DIR)
    if not pages_dir.exists():
        return pages
    for file_path in pages_dir.rglob("*.md"):
        if file_path.is_file():
            pages.append(file_path.relative_to(project_dir).as_posix())
    return sorted(pages)


def page_catalog() -> list[dict]:
    """Return editable pages in manifest order with human-readable titles."""
    manifest_path = Path(PROJECT_DIR) / "data" / "srd.yaml"
    if not manifest_path.is_file():
        return []
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    available = set(list_pages())
    catalog = []
    for item in manifest.get("pages", []):
        entries = item.get("subs") or [item]
        for entry in entries:
            path = str(entry.get("path", "")).strip("/")
            if not path:
                continue
            files = {
                language: f"src/pages/{path}/{language}.md"
                for language in ("zh", "en")
                if f"src/pages/{path}/{language}.md" in available
            }
            if files:
                catalog.append({"path": path, "title": entry.get("title", {}), "files": files})
    return catalog


def _resolve_path(path: str) -> Path | None:
    if not isinstance(path, str) or not path.startswith("src/pages/") or not path.endswith(".md"):
        return None
    try:
        pages_root = Path(PAGES_DIR).resolve()
        candidate = (Path(PROJECT_DIR) / Path(path)).resolve()
        candidate.relative_to(pages_root)
    except (OSError, ValueError):
        return None
    return candidate


def read_file(path: str) -> str | None:
    full = _resolve_path(path)
    if not full or not full.is_file():
        return None
    return full.read_text(encoding="utf-8")


class PublishError(RuntimeError):
    def __init__(self, message: str, status: int = 400, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.details = details or {}


class GitSync:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.state_path = project_dir / "var" / "git-sync.json"
        self.lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self.state = self._load()
        if self.state.get("status") in {"pending", "retrying"}:
            self._start_worker()

    def _load(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"status": "idle", "updatedAt": utc_now(), "error": ""}

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.state_path)

    def queue(self, commit: str) -> None:
        with self.lock:
            self.state = {"status": "pending", "commit": commit, "updatedAt": utc_now(), "error": ""}
            self._save()
        self._start_worker()

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.state)

    def _start_worker(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._push_with_retry, daemon=True)
        self._worker.start()

    def _push_with_retry(self) -> None:
        delay = 0
        while True:
            if delay:
                time.sleep(delay)
            try:
                result = subprocess.run(
                    ["git", "push"], cwd=self.project_dir, capture_output=True,
                    text=True, timeout=60, encoding="utf-8", errors="replace",
                )
                if result.returncode == 0:
                    with self.lock:
                        self.state.update(status="synced", updatedAt=utc_now(), error="")
                        self._save()
                    return
                last_error = (result.stderr or result.stdout).strip()
            except (OSError, subprocess.TimeoutExpired) as exc:
                last_error = str(exc)
            with self.lock:
                self.state.update(
                    status="retrying",
                    updatedAt=utc_now(),
                    error=last_error or "git push failed",
                )
                self._save()
            delay = 3 if delay == 0 else min(delay * 5, 300)


GIT_SYNC = GitSync(PROJECT_DIR)


def _copy_candidate_project(destination: Path) -> None:
    for directory in ("data", "layouts", "static", "src"):
        source = PROJECT_DIR / directory
        if source.exists():
            shutil.copytree(source, destination / directory)
    shutil.copy2(PROJECT_DIR / "config.yaml", destination / "config.yaml")


def _run_candidate_build(candidate: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT), "--project-dir", str(candidate)],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=180,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise PublishError(f"构建失败:\n{details}")
    if not (candidate / "public" / "index.html").is_file():
        raise PublishError("构建未生成完整站点")


def _commit_changes(paths: list[str], display_name: str) -> str:
    message = f"编辑 {len(paths)} 个页面 ({display_name})"
    result = subprocess.run(
        ["git", "commit", "--only", "-m", message, "--", *paths],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise PublishError(f"本地版本记录失败: {(result.stderr or result.stdout).strip()}", status=500)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_DIR, capture_output=True,
        text=True, timeout=10, encoding="utf-8", errors="replace",
    )
    if revision.returncode != 0:
        raise PublishError("无法读取发布版本", status=500)
    return revision.stdout.strip()


def publish_changes(changes: list[dict], display_name: str) -> dict:
    display_name = display_name.strip() if isinstance(display_name, str) else ""
    if not display_name:
        raise PublishError("编辑者名称不能为空")
    if not isinstance(changes, list) or not changes:
        raise PublishError("没有需要发布的页面")
    with PUBLISH_LOCK:
        prepared = []
        conflicts = []
        seen_paths = set()
        for change in changes:
            if not isinstance(change, dict):
                raise PublishError("页面修改格式无效")
            path = change.get("path", "")
            if path in seen_paths:
                raise PublishError(f"页面重复提交: {path}")
            seen_paths.add(path)
            full = _resolve_path(path)
            if not full or not full.is_file():
                raise PublishError("只允许编辑现有的 src/pages Markdown 文件")
            content = change.get("content", "")
            if not isinstance(content, str) or not content.strip():
                raise PublishError(f"内容不能为空: {path}")
            if len(content.encode("utf-8")) > MAX_JSON_BYTES:
                raise PublishError(f"内容过大: {path}")
            current_content = full.read_text(encoding="utf-8")
            current_version = content_version(current_content)
            base_version = change.get("baseVersion")
            if base_version and base_version != current_version:
                conflicts.append({
                    "path": path,
                    "currentContent": current_content,
                    "currentVersion": current_version,
                })
            prepared.append({
                "path": path,
                "full": full,
                "content": content,
                "currentContent": current_content,
                "currentVersion": current_version,
            })
        if conflicts:
            raise PublishError(
                "变更集中有页面已被其他人修改，请合并后重新发布",
                status=409,
                details={"conflicts": conflicts},
            )

        changed = [item for item in prepared if item["content"] != item["currentContent"]]
        versions = {
            item["path"]: content_version(item["content"])
            for item in prepared
        }
        if not changed:
            return {"message": "内容没有变化", "versions": versions, "gitSync": GIT_SYNC.snapshot()}

        with tempfile.TemporaryDirectory(prefix="srd-publish-", dir=PROJECT_DIR) as temp_name:
            candidate = Path(temp_name)
            _copy_candidate_project(candidate)
            for item in changed:
                candidate_file = candidate / item["path"]
                candidate_file.parent.mkdir(parents=True, exist_ok=True)
                candidate_file.write_text(item["content"], encoding="utf-8")
            _run_candidate_build(candidate)

            pending_sources = []
            for item in changed:
                pending = item["full"].with_name(f".{item['full'].name}.{uuid.uuid4().hex}.pending")
                pending.write_text(item["content"], encoding="utf-8")
                pending_sources.append((item, pending))
            public_backup = PROJECT_DIR / f".public-backup-{uuid.uuid4().hex}"
            replaced_sources = []
            public_changed = False
            try:
                for item, pending in pending_sources:
                    os.replace(pending, item["full"])
                    replaced_sources.append(item)
                if PUBLIC_DIR.exists():
                    os.replace(PUBLIC_DIR, public_backup)
                os.replace(candidate / "public", PUBLIC_DIR)
                public_changed = True
                commit = _commit_changes([item["path"] for item in changed], display_name)
            except Exception:
                if public_changed and PUBLIC_DIR.exists():
                    shutil.rmtree(PUBLIC_DIR)
                if public_backup.exists():
                    os.replace(public_backup, PUBLIC_DIR)
                for item in replaced_sources:
                    item["full"].write_text(item["currentContent"], encoding="utf-8")
                for _item, pending in pending_sources:
                    if pending.exists():
                        pending.unlink()
                raise
            finally:
                if public_backup.exists():
                    shutil.rmtree(public_backup)

        GIT_SYNC.queue(commit)
        return {
            "message": "保存成功，站点已更新",
            "versions": versions,
            "commit": commit,
            "gitSync": GIT_SYNC.snapshot(),
        }


def publish_edit(path: str, content: str, base_version: str | None, display_name: str) -> dict:
    result = publish_changes([{
        "path": path,
        "content": content,
        "baseVersion": base_version,
    }], display_name)
    result["version"] = result["versions"].get(path)
    return result


def save_and_build(path: str, content: str, base_version: str | None = None, display_name: str = "shared-editor"):
    """Compatibility wrapper used by older callers and tests."""
    try:
        result = publish_edit(path, content, base_version, display_name)
        return True, result["message"]
    except PublishError as exc:
        return False, str(exc)


class FeedbackStore:
    STATUSES = {"pending", "in_progress", "accepted", "closed"}

    def __init__(self, database_path: Path):
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    contact TEXT NOT NULL DEFAULT '',
                    page_path TEXT NOT NULL,
                    anchor TEXT NOT NULL,
                    language TEXT NOT NULL,
                    site_version TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    internal_note TEXT NOT NULL DEFAULT '',
                    is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def create(self, payload: dict) -> int:
        now = utc_now()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO feedback
                   (message, contact, page_path, anchor, language, site_version, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    payload["message"], payload.get("contact", ""), payload.get("path", ""),
                    payload.get("anchor", "top"), payload.get("language", "zh"),
                    payload.get("version", "current"), now, now,
                ),
            )
            return int(cursor.lastrowid)

    def list(self, status: str | None = None) -> list[dict]:
        query = "SELECT * FROM feedback"
        params: tuple = ()
        if status in self.STATUSES:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY created_at DESC"
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]

    def update(self, feedback_id: int, status: str, note: str, is_read: bool = True) -> bool:
        if status not in self.STATUSES:
            raise ValueError("无效状态")
        with self.connect() as connection:
            result = connection.execute(
                """UPDATE feedback SET status = ?, internal_note = ?, is_read = ?, updated_at = ?
                   WHERE id = ?""",
                (status, note[:4000], int(is_read), utc_now(), feedback_id),
            )
            return result.rowcount == 1


FEEDBACK_STORE = FeedbackStore(FEEDBACK_DB)
RATE_LIMIT: dict[str, deque] = defaultdict(deque)
RATE_LOCK = threading.Lock()


def allow_feedback(ip_address: str, limit: int = 5, window_seconds: int = 600) -> bool:
    now = time.monotonic()
    with RATE_LOCK:
        attempts = RATE_LIMIT[ip_address]
        while attempts and now - attempts[0] > window_seconds:
            attempts.popleft()
        if len(attempts) >= limit:
            return False
        attempts.append(now)
        return True


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "DaggerheartSRD/2"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/page-list":
            self._json(200, {"pages": page_catalog()})
        elif parsed.path == "/api/get-file":
            path = parse_qs(parsed.query).get("path", [""])[0]
            if not path:
                self._json(400, {"error": "缺少 path 参数"})
                return
            content = read_file(path)
            if content is None:
                self._json(404, {"error": f"文件不存在或不可访问: {path}"})
            else:
                self._json(200, {"content": content, "version": content_version(content)})
        elif parsed.path == "/api/admin/publish-status":
            self._json(200, {"gitSync": GIT_SYNC.snapshot()})
        elif parsed.path == "/api/admin/feedback":
            status = parse_qs(parsed.query).get("status", [None])[0]
            records = FEEDBACK_STORE.list(status)
            self._json(200, {"feedback": records, "unread": sum(not item["is_read"] for item in records)})
        elif parsed.path == "/api/admin/feedback/export":
            self._json(200, {"exportedAt": utc_now(), "feedback": FEEDBACK_STORE.list()})
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self._read_json()
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
            return

        if parsed.path == "/api/save":
            try:
                changes = data.get("changes")
                if not isinstance(changes, list):
                    changes = [{
                        "path": data.get("path", ""),
                        "content": data.get("content", ""),
                        "baseVersion": data.get("baseVersion"),
                    }]
                result = publish_changes(changes, str(data.get("displayName", ""))[:80])
                self._json(200, result)
            except PublishError as exc:
                self._json(exc.status, {"error": str(exc), **exc.details})
            except Exception as exc:
                self._json(500, {"error": f"发布异常: {exc}"})
        elif parsed.path == "/api/feedback":
            self._submit_feedback(data)
        elif parsed.path == "/api/admin/feedback/update":
            try:
                feedback_id = int(data.get("id"))
                changed = FEEDBACK_STORE.update(feedback_id, data.get("status", "pending"), str(data.get("note", "")))
                self._json(200 if changed else 404, {"updated": changed} if changed else {"error": "反馈不存在"})
            except (TypeError, ValueError) as exc:
                self._json(400, {"error": str(exc)})
        else:
            self._json(404, {"error": "Not found"})

    def _submit_feedback(self, data: dict) -> None:
        ip_address = self.headers.get("X-Real-IP") or self.client_address[0]
        if data.get("website"):
            self._json(201, {"received": True})
            return
        if not allow_feedback(ip_address):
            self._json(429, {"error": "提交过于频繁，请稍后再试"})
            return
        message = data.get("message", "")
        contact = data.get("contact", "")
        if not isinstance(message, str) or not message.strip() or len(message) > 4000:
            self._json(400, {"error": "问题描述不能为空且不能超过 4000 字"})
            return
        if not isinstance(contact, str) or len(contact) > 200:
            self._json(400, {"error": "联系方式不能超过 200 字"})
            return
        data["message"] = message.strip()
        data["contact"] = contact.strip()
        feedback_id = FEEDBACK_STORE.create(data)
        self._json(201, {"received": True, "id": feedback_id})

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("无效的 Content-Length") from exc
        if length <= 0 or length > MAX_JSON_BYTES:
            raise ValueError("请求内容为空或过大")
        try:
            value = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("无效的 JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON 必须是对象")
        return value

    def _json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {args[0]}")


def run_startup_build() -> bool:
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)], cwd=PROJECT_DIR,
        capture_output=True, text=True, timeout=180,
        encoding="utf-8", errors="replace",
    )
    if result.returncode == 0:
        print("启动构建成功")
        return True
    print(f"启动构建失败:\n{result.stderr or result.stdout}", file=sys.stderr)
    return False


if __name__ == "__main__":
    run_startup_build()
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    print(f"SRD 管理服务已启动: http://{LISTEN_HOST}:{LISTEN_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()
