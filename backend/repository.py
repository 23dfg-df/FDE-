"""SQLite 实验记录与原子 JSON 文件写入。"""

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class Repository:
    def __init__(self, data: Path):
        data.mkdir(parents=True, exist_ok=True)
        self.path = data / "history.sqlite3"
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS records("
                "id TEXT PRIMARY KEY, kind TEXT, created_at TEXT, payload TEXT)"
            )

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def save(self, kind, value):
        record = {"id": str(uuid.uuid4()), "created_at": now(), **value, "kind": kind}
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO records VALUES(?,?,?,?)",
                (
                    record["id"],
                    kind,
                    record["created_at"],
                    json.dumps(record, ensure_ascii=False),
                ),
            )
        return record

    def list(self, kind=None, limit=500):
        with self.connect() as connection:
            if kind:
                rows = connection.execute(
                    "SELECT payload FROM records WHERE kind=? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (kind, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload FROM records ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def backup(self, destination: Path):
        with self.connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
