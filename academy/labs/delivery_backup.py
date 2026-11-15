"""临时 SQLite 备份恢复实验；不接触项目业务数据库。Python 3.10+。"""
import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(source, target):
    source = Path(source)
    target = Path(target)
    if target.exists():
        raise FileExistsError("backup target already exists")
    if not source.is_file():
        raise FileNotFoundError(source)
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
    return {"sha256": digest(target), "bytes": target.stat().st_size}


def restore(backup, target, expected_sha256):
    backup, target = Path(backup), Path(target)
    if digest(backup) != expected_sha256:
        raise ValueError("backup integrity mismatch")
    if target.exists():
        raise FileExistsError("restore target must be new")
    with closing(sqlite3.connect(backup.resolve().as_uri() + "?mode=ro", uri=True)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("restored database integrity failure")
    return target


def demo():
    with tempfile.TemporaryDirectory(prefix="fde-backup-") as folder:
        root = Path(folder)
        source, backup, recovered = [root / n for n in ("source.db", "snapshot.db", "restored.db")]
        with closing(sqlite3.connect(source)) as db, db:
            db.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, title TEXT)")
            db.execute("INSERT INTO documents VALUES (?, ?)", (1, "教学通知"))
        manifest = snapshot(source, backup)
        with closing(sqlite3.connect(source)) as db, db:
            db.execute("INSERT INTO documents VALUES (?, ?)", (2, "备份后的新记录"))
        restore(backup, recovered, manifest["sha256"])
        with closing(sqlite3.connect(recovered)) as db:
            rows = db.execute("SELECT id, title FROM documents ORDER BY id").fetchall()
        return {"scope": "temporary_sqlite_teaching_lab", "backup": manifest,
                "restored_rows": rows, "missing_after_snapshot_ids": [2],
                "observation": "恢复的是备份时刻，不包含之后新增的记录。"}


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
