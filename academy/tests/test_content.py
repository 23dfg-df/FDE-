"""Validate curriculum coverage and portable artifact behavior."""
import json
import re
import sys
import tempfile
import unittest
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
            self.assertEqual(len(list((root / "docs").glob("*.md"))), 39)
            for path in (root / "docs").glob("*.md"):
                for ref in re.findall(r'\]\(([^)]+)\)', path.read_text("utf-8")):
                    if "://" not in ref and not ref.startswith("#"):
                        target = (ROOT / ref[3:]) if ref.startswith("../") else path.parent / ref
                        self.assertTrue(target.is_file(), (path.name, ref))

    def test_public_content_has_no_personal_environment_values(self):
        text = json.dumps(self.data, ensure_ascii=False)
        self.assertNotRegex(text, r"/(?:Users|home)/(?!learner|student)[^/\s]+|\b(?:ghp_|github_pat_)\w+|BEGIN OPENSSH PRIVATE KEY")


if __name__ == "__main__": unittest.main()
