"""临时 SQLite 事务、参数绑定与执行计划实验；不接触业务数据库。"""

import json
import sqlite3
import tempfile
from pathlib import Path


def insert_batch(connection, rows):
    try:
        connection.execute("BEGIN")
        connection.executemany("INSERT INTO notes(title) VALUES (?)", [(x,) for x in rows])
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def run_demo():
    with tempfile.TemporaryDirectory(prefix="fde-sql-") as directory:
        connection = sqlite3.connect(str(Path(directory) / "lesson.db"), isolation_level=None)
        try:
            connection.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, title TEXT NOT NULL UNIQUE)")
            rejected = False
            try:
                insert_batch(connection, ["API", "API"])
            except sqlite3.IntegrityError:
                rejected = True
            after_failed_batch = connection.execute("SELECT count(*) FROM notes").fetchone()[0]
            insert_batch(connection, ["API", "SQL"])
            literal = "' OR 1=1 --"
            injection_matches = connection.execute("SELECT title FROM notes WHERE title = ?", (literal,)).fetchall()
            # 单独的非唯一列展示索引前后的计划，避免唯一约束隐式索引干扰。
            connection.execute("CREATE TABLE observations (topic TEXT, duration INTEGER)")
            connection.executemany("INSERT INTO observations VALUES (?, ?)", [("api" if i % 2 else "sql", i) for i in range(100)])
            query = "EXPLAIN QUERY PLAN SELECT duration FROM observations WHERE topic = ?"
            before = [row[3] for row in connection.execute(query, ("api",))]
            connection.execute("CREATE INDEX idx_topic ON observations(topic)")
            after = [row[3] for row in connection.execute(query, ("api",))]
            return {"scope": "temporary_sqlite_teaching_experiment", "duplicate_rejected": rejected,
                    "rows_after_failed_batch": after_failed_batch,
                    "committed_rows": connection.execute("SELECT title FROM notes ORDER BY id").fetchall(),
                    "literal_input_matches": len(injection_matches), "plan_without_index": before,
                    "plan_with_index": after, "performance_claim": "not_measured"}
        finally:
            connection.close()


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
