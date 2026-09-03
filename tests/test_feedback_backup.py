import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backup_feedback


def make_database(path: Path) -> None:
    with sqlite3.connect(path) as database:
        database.execute("CREATE TABLE feedback (id INTEGER PRIMARY KEY, message TEXT NOT NULL)")
        database.execute("INSERT INTO feedback (message) VALUES (?)", ("保留这条反馈",))


def test_online_backup_creates_a_readable_consistent_snapshot(tmp_path):
    source = tmp_path / "feedback.db"
    destination_dir = tmp_path / "backups"
    make_database(source)

    snapshot = backup_feedback.create_backup(
        source,
        destination_dir,
        datetime(2026, 9, 3, 3, 20, tzinfo=timezone.utc),
    )

    assert snapshot.name == "feedback-20260903T032000Z.sqlite3"
    with sqlite3.connect(snapshot) as database:
        assert database.execute("PRAGMA quick_check").fetchone() == ("ok",)
        assert database.execute("SELECT message FROM feedback").fetchone() == ("保留这条反馈",)


def test_pruning_removes_only_expired_named_snapshots_and_keeps_latest(tmp_path):
    now = datetime(2026, 9, 3, tzinfo=timezone.utc)
    old = tmp_path / "feedback-20260701T000000Z.sqlite3"
    latest = tmp_path / "feedback-20260903T000000Z.sqlite3"
    unrelated = tmp_path / "manual-copy.sqlite3"
    for path in (old, latest, unrelated):
        path.write_bytes(b"test")
    old_timestamp = (now - timedelta(days=60)).timestamp()
    os.utime(old, (old_timestamp, old_timestamp))

    removed = backup_feedback.prune_backups(tmp_path, 30, now)

    assert removed == [old]
    assert not old.exists()
    assert latest.exists()
    assert unrelated.exists()


def test_backup_location_cannot_be_inside_public_project_tree(tmp_path):
    project = tmp_path / "SRD"
    project.mkdir()
    with pytest.raises(backup_feedback.BackupError, match="不得位于站点项目目录内"):
        backup_feedback.validate_backup_location(project / "public" / "backups", project)
