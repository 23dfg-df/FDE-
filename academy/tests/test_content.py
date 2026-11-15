"""Validate curriculum coverage and portable artifact behavior."""
import copy
import json
import re
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


class CurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data = build.load_data()

    def test_complete_outline_preserved(self):
        original = [(m["id"], topic) for m in self.data["outline"]["modules"] for topic in m["topics"]]
        actual = [(row["module"], row["topic"]) for row in self.data["coverage"]]
        self.assertEqual(original, actual)
        self.assertEqual(len(actual), 110)

    def test_curriculum_is_core_plus_advanced(self):
        lessons = self.data["lessons"]
        self.assertEqual(len(lessons), 36)
        self.assertEqual(sum(x["hours"] for x in lessons if x["level"] == "core"), 108)
        self.assertEqual(sum(x["hours"] for x in lessons if x["level"] == "advanced"), 144)
        assigned = [lid for w in self.data["advancedWeeks"] for lid in w["lessons"]]
        self.assertEqual(set(assigned), {x["id"] for x in lessons if x["level"] == "advanced"})
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_all_exercises_have_gradual_help_and_evidence(self):
        for lesson in self.data["lessons"]:
            with self.subTest(lesson=lesson["id"]):
                exercise = lesson["exercise"]
                self.assertGreaterEqual(len(exercise["steps"]), 2)
                self.assertGreaterEqual(len(exercise["hints"]), 1)
                self.assertGreaterEqual(len(exercise["acceptance"]), 2)
                self.assertTrue(exercise["deliverable"])
                self.assertGreaterEqual(len(lesson["quiz"]), 2)

    def test_practice_plan_replaces_course_budget_and_matches_calendar(self):
        phases = self.data["practice"]["phases"]
        self.assertEqual([p["hours"] for p in phases], [14, 28, 16, 24, 28, 16])
        self.assertEqual(sum(p["hours"] for p in phases), 126)
        self.assertEqual(len({p["id"] for p in phases}), 6)
        lesson_ids = {lesson["id"] for lesson in self.data["lessons"]}
        next_start = date(2026, 11, 16)
        for phase in phases:
            with self.subTest(phase=phase["id"]):
                start, end = date.fromisoformat(phase["start"]), date.fromisoformat(phase["end"])
                self.assertEqual(start, next_start)
                days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
                self.assertEqual(sum(2 if d < date(2026, 12, 15) else 4 for d in days), phase["hours"])
                self.assertEqual(phase["level"], "core")
                self.assertTrue(phase["outcome"].strip())
                self.assertTrue(phase["lessons"])
                self.assertTrue(set(phase["lessons"]).issubset(lesson_ids))
                next_start = end + timedelta(days=1)
        self.assertEqual(next_start, date(2027, 1, 1))

    def test_advanced_practice_has_three_consecutive_four_week_blocks(self):
        advanced = self.data["practice"]["advanced"]
        self.assertEqual([phase["hours"] for phase in advanced], [80, 80, 80])
        next_start = date(2027, 1, 1)
        for phase in advanced:
            start, end = date.fromisoformat(phase["start"]), date.fromisoformat(phase["end"])
            self.assertEqual(start, next_start)
            self.assertEqual((end - start).days + 1, 28)
            self.assertTrue(phase["focus"].strip())
            next_start = end + timedelta(days=1)
        self.assertEqual(next_start, date(2027, 3, 26))

    def test_practice_document_keeps_acceptance_and_unimplemented_boundaries(self):
        document = self.data["practice"]["document"]
        markdown = document["markdown"]
        for text in ("独立修改一个功能", "独立定位并修复一次故障", "同学按照手册独立跑通",
                     "尚未实现或执行", "辅助完成", "48 小时", "连续三轮", "未执行"):
            self.assertIn(text, markdown)
        self.assertIn(".venv-app/bin/python -m pytest tests -q", markdown)
        blocks = document["blocks"]
        allowed = {"heading", "paragraph", "list", "table", "code"}
        self.assertEqual({block["type"] for block in blocks}, allowed)
        headings = [block for block in blocks if block["type"] == "heading"]
        self.assertEqual(len({block["id"] for block in headings}), len(headings))
        self.assertTrue(all(block["id"].startswith("practice-section-") for block in headings))
        self.assertTrue(any("pytest tests -q" in block["text"] for block in blocks if block["type"] == "code"))
        for block in blocks:
            if block["type"] == "table":
                self.assertTrue(block["headers"])
                self.assertTrue(all(len(row) == len(block["headers"]) for row in block["rows"]))

    def test_invalid_practice_budget_and_lesson_reference_are_rejected(self):
        data = copy.deepcopy(self.data)
        data["practice"]["phases"][0]["hours"] += 1
        with self.assertRaises(ValueError):
            build.validate(data)
        data = copy.deepcopy(self.data)
        data["practice"]["phases"][0]["lessons"].append("unknown-lesson")
        with self.assertRaises(ValueError):
            build.validate(data)

    def test_single_html_is_self_contained_and_embedded_data_survives(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "index.html"
            build.build(path)
            html = path.read_text("utf-8")
            self.assertNotRegex(html, r'<script[^>]+src=|<link[^>]+stylesheet|@import\s')
            match = re.search(r'<script id="knowledge-data" type="application/json">(.*?)</script>', html, re.S)
            self.assertIsNotNone(match)
            embedded = json.loads(match.group(1))
            self.assertEqual(embedded, self.data)
            self.assertNotIn("__KNOWLEDGE__", html)

    def test_markdown_references_point_to_generated_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            build.build(root / "index.html", root / "docs")
            self.assertEqual(len(list((root / "docs").glob("*.md"))), 40)
            self.assertEqual((root / "docs/PRACTICE.md").read_text("utf-8"), self.data["practice"]["document"]["markdown"])
            self.assertIn("(PRACTICE.md)", (root / "docs/README.md").read_text("utf-8"))
            for path in (root / "docs").glob("*.md"):
                for ref in re.findall(r'\]\(([^)]+)\)', path.read_text("utf-8")):
                    if "://" not in ref and not ref.startswith("#"):
                        target = (ROOT / ref[3:]) if ref.startswith("../") else path.parent / ref
                        self.assertTrue(target.is_file(), (path.name, ref))

    def test_public_content_has_no_personal_environment_values(self):
        text = json.dumps(self.data, ensure_ascii=False)
        self.assertNotRegex(text, r"/(?:Users|home)/(?!learner|student)[^/\s]+|\b(?:ghp_|github_pat_)\w+|BEGIN OPENSSH PRIVATE KEY")


if __name__ == "__main__": unittest.main()
