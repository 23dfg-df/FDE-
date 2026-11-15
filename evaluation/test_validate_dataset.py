"""用独立损坏样本验证题库审计能发现证据漂移与划分污染。"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from validate_dataset import validate


class DatasetValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        source = Path(__file__).resolve().parents[1]
        shutil.copytree(source / "corpus", self.root / "corpus")
        (self.root / "evaluation").mkdir()
        for name in ("questions.json", "corpus-manifest.json"):
            shutil.copy2(source / "evaluation" / name, self.root / "evaluation" / name)
        self.question_path = self.root / "evaluation/questions.json"
        self.payload = json.loads(self.question_path.read_text("utf-8"))

    def write_changes(self):
        self.question_path.write_text(
            json.dumps(self.payload, ensure_ascii=False), encoding="utf-8"
        )

    def test_reference_dataset_is_valid(self):
        result = validate(self.root)
        self.assertEqual(result["status"], "passed", result["errors"])
        self.assertEqual(result["question_count"], 50)

    def test_changed_source_fact_invalidates_reference_quote(self):
        source = self.root / "corpus/server-snapshot-20261115.md"
        source.write_text(
            source.read_text("utf-8").replace("32607 MiB", "32000 MiB"),
            encoding="utf-8",
        )
        result = validate(self.root)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("不是原文连续片段" in error for error in result["errors"]))

    def test_duplicate_question_across_splits_is_rejected(self):
        self.payload["questions"][1]["question"] = self.payload["questions"][0][
            "question"
        ]
        self.write_changes()
        self.assertTrue(any("跨划分重复" in e for e in validate(self.root)["errors"]))

    def test_invented_source_is_rejected(self):
        self.payload["questions"][0]["expected_evidence"][0]["source"] = "made-up.md"
        self.write_changes()
        self.assertTrue(any("未知证据来源" in e for e in validate(self.root)["errors"]))

    def test_unanswerable_question_with_gold_evidence_is_rejected(self):
        item = next(q for q in self.payload["questions"] if not q["answerable"])
        item["expected_sources"] = self.payload["questions"][0]["expected_sources"]
        item["expected_evidence"] = self.payload["questions"][0]["expected_evidence"]
        self.write_changes()
        self.assertTrue(any("无答案题不应" in e for e in validate(self.root)["errors"]))


if __name__ == "__main__":
    unittest.main()
