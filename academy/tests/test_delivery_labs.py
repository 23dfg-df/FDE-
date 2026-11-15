import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "labs" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


backup = module("delivery_backup")
logs = module("delivery_logs")
capacity = module("delivery_capacity")


class BackupTests(unittest.TestCase):
    def test_missing_source_does_not_create_empty_database(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "missing.db"
            with self.assertRaises(FileNotFoundError):
                backup.snapshot(source, Path(folder) / "backup.db")
            self.assertFalse(source.exists())

    def test_snapshot_restores_only_committed_snapshot(self):
        self.assertEqual(backup.demo()["restored_rows"], [(1, "教学通知")])

    def test_corrupted_backup_rejected_before_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "source.db"
            with sqlite3.connect(p) as db:
                db.execute("CREATE TABLE notes (id INTEGER)")
            target = Path(folder) / "backup.db"
            m = backup.snapshot(p, target)
            target.write_bytes(target.read_bytes() + b"corrupt")
            with self.assertRaises(ValueError):
                backup.restore(target, Path(folder) / "restore.db", m["sha256"])
            self.assertFalse((Path(folder) / "restore.db").exists())

    def test_snapshot_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "keep.txt"
            p.write_text("keep")
            with self.assertRaises(FileExistsError):
                backup.snapshot(Path(folder) / "source.db", p)
            self.assertEqual(p.read_text(), "keep")


class LogTests(unittest.TestCase):
    def test_interleaved_requests_are_separate(self):
        result = logs.demo()
        self.assertEqual(result["requests"][0]["total_ms"], 1950)
        self.assertEqual(result["requests"][1]["failed_stages"], ["model", "request"])
        self.assertEqual(result["rejected_line_numbers"], [7])

    def test_missing_root_is_unknown_not_sum(self):
        line = json.dumps({"request_id": "x", "stage": "child", "status": "ok", "duration_ms": 30})
        self.assertIsNone(logs.summarize([line])["requests"][0]["total_ms"])

    def test_invalid_measurement_rejected(self):
        items = [True, -1, float("nan"), "30"]
        lines = [json.dumps({"request_id": "x", "stage": "child", "status": "ok", "duration_ms": x}) for x in items]
        self.assertEqual(logs.summarize(lines)["rejected_line_numbers"], [1, 2, 3, 4])


class CapacityTests(unittest.TestCase):
    def test_serial_worker_arithmetic(self):
        self.assertEqual(capacity.capacity(2, 0.5, 0.5)["serial_workers_lower_estimate"], 2)

    def test_invalid_utilization_and_numbers(self):
        for value in [0, 1, -1, float("nan"), True]:
            with self.assertRaises(ValueError):
                capacity.capacity(2, 0.5, value)

    def test_token_cost_separates_input_and_output(self):
        r = capacity.cost(100_000, 1000, 200, 2, 6, 720, 1, 80)
        self.assertAlmostEqual(r["api_cost"], 320)
        self.assertAlmostEqual(r["break_even_requests"], 250_000)

    def test_zero_token_price_has_no_crossing(self):
        self.assertIsNone(capacity.cost(0, 1000, 200, 0, 0, 1, 1, 0)["break_even_requests"])

    def test_request_error_budget(self):
        self.assertEqual(capacity.error_budget(10000, 0.99)["allowed_bad_requests"], 100)


if __name__ == "__main__":
    unittest.main()
