import asyncio
import importlib.util
from pathlib import Path
import unittest


def load(name):
    path = Path(__file__).resolve().parents[1] / "labs" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sql = load("engineering_sql")
jobs = load("engineering_async")
http = load("engineering_http")


class DatabaseTests(unittest.TestCase):
    def test_failed_batch_has_no_partial_rows(self):
        result = sql.run_demo()
        self.assertTrue(result["duplicate_rejected"])
        self.assertEqual(result["rows_after_failed_batch"], 0)
        self.assertEqual(result["committed_rows"], [("API",), ("SQL",)])

    def test_input_is_a_value_and_plan_changes(self):
        result = sql.run_demo()
        self.assertEqual(result["literal_input_matches"], 0)
        self.assertTrue(any("SCAN" in plan for plan in result["plan_without_index"]))
        self.assertTrue(any("INDEX" in plan for plan in result["plan_with_index"]))


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_bounded_workers_preserve_results(self):
        result = await jobs.run_jobs(count=8, workers=2)
        self.assertLessEqual(result["stats"]["peak"], 2)
        self.assertEqual([r["value"] for r in result["results"]], list(range(0, 16, 2)))
        self.assertEqual(result["stats"]["active"], 0)

    async def test_failure_is_visible_not_dropped(self):
        result = await jobs.run_jobs(fail_at=2)
        self.assertEqual(result["results"][2]["status"], "failed")
        self.assertEqual(sum(x["status"] == "completed" for x in result["results"]), 5)

    async def test_cancel_drains_workers(self):
        result = await jobs.demo()
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["after_cancel"]["active"], 0)
        self.assertEqual(result["after_cancel"]["workers_stopped"], 2)

    async def test_invalid_limits_rejected(self):
        with self.assertRaises(ValueError):
            await jobs.run_jobs(workers=0)


class HttpTests(unittest.TestCase):
    def test_repeat_and_conflict_do_not_duplicate(self):
        with http.local_server() as (url, repository):
            first = http.send(url, {"title": "通知"})
            second = http.send(url, {"title": "通知"})
            conflict = http.send(url, {"title": "不同"})
            self.assertEqual([first[0], second[0], conflict[0]], [201, 200, 409])
            self.assertEqual(first[1]["item"], second[1]["item"])
            self.assertEqual(len(repository.items), 1)

    def test_invalid_body_and_path(self):
        with http.local_server() as (url, repository):
            for payload in [{"title": " "}, {"title": 42}, [], {"title": "x" * 81}]:
                self.assertEqual(http.send(url, payload)[0], 422)
            self.assertEqual(http.send(url, {"title": "ok"}, path="/wrong")[0], 404)
            self.assertEqual(len(repository.items), 0)


if __name__ == "__main__":
    unittest.main()
