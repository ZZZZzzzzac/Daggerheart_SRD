"""Create and retain consistent SQLite snapshots of the feedback inbox."""

from __future__ import annotations

import argparse
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE = PROJECT_DIR / "var" / "feedback.db"
DEFAULT_BACKUP_DIR = Path("/var/backups/daggerheart-srd")
BACKUP_PREFIX = "feedback-"
BACKUP_SUFFIX = ".sqlite3"


class BackupError(RuntimeError):
    pass


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_backup_location(backup_dir: Path, project_dir: Path = PROJECT_DIR) -> None:
    if _is_within(backup_dir, project_dir):
        raise BackupError(f"备份目录不得位于站点项目目录内: {backup_dir}")


def create_backup(database: Path, backup_dir: Path, now: datetime | None = None) -> Path:
    if not database.is_file():
        raise BackupError(f"反馈数据库不存在: {database}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"{BACKUP_PREFIX}{timestamp}{BACKUP_SUFFIX}"
    temporary = backup_dir / f".{destination.name}.{os.getpid()}.tmp"
    if destination.exists():
        raise BackupError(f"备份文件已存在: {destination}")
    try:
        with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(temporary)) as target:
            with target:
                source.backup(target)
        with closing(sqlite3.connect(f"file:{temporary.as_posix()}?mode=ro", uri=True)) as snapshot:
            result = snapshot.execute("PRAGMA quick_check").fetchone()
        if result != ("ok",):
            raise BackupError(f"SQLite 快照完整性检查失败: {result}")
        os.replace(temporary, destination)
        try:
            destination.chmod(0o600)
        except OSError:
            pass
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def prune_backups(backup_dir: Path, retention_days: int, now: datetime | None = None) -> list[Path]:
    if retention_days < 1:
        raise BackupError("保留天数必须至少为 1")
    cutoff = (now or datetime.now(timezone.utc)).timestamp() - timedelta(days=retention_days).total_seconds()
    candidates = sorted(backup_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"), reverse=True)
    removed = []
    for path in candidates[1:]:
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink()
            removed.append(path)
    return removed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--retention-days", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_backup_location(args.backup_dir)
        destination = create_backup(args.database, args.backup_dir)
        removed = prune_backups(args.backup_dir, args.retention_days)
    except (BackupError, OSError, sqlite3.Error) as exc:
        print(f"反馈数据库备份失败: {exc}")
        return 1
    print(f"反馈数据库备份完成: {destination}")
    if removed:
        print(f"已清理 {len(removed)} 个过期备份")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
