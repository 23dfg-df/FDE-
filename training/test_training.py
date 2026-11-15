"""验证数据隔离和规则评分的关键边界，不需要 GPU。"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from common import load_data, score_answer, summarize


class TrainingDataTests(unittest.TestCase):
    def test_dataset_counts_and_disjoint_families(self):
        groups, audit = load_data(Path(__file__).resolve().parent / "data")
        self.assertEqual(audit["counts"], {"train": 80, "validation": 16, "test": 20})
        self.assertTrue(audit["template_families_disjoint"])
        self.assertEqual(len(groups["test"]), 20)

    def test_family_leak_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            target = Path(name) / "data"
            shutil.copytree(Path(__file__).resolve().parent / "data", target)
            path = target / "test.jsonl"
            rows = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
            rows[0]["template_family"] = "brief"
            path.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "模板家庭"):
                load_data(target)

    def test_correct_answer_is_full_pass(self):
        target = {"category": "gpu_oom", "next_check": "inspect_gpu_memory"}
        self.assertTrue(all(score_answer(json.dumps(target), target).values()))

    def test_correct_category_wrong_action_is_not_joint_pass(self):
        target = {"category": "gpu_oom", "next_check": "inspect_gpu_memory"}
        score = score_answer(
            '{"category":"gpu_oom","next_check":"verify_model_path"}', target
        )
        self.assertTrue(score["category"])
        self.assertFalse(score["next_check"])
        self.assertFalse(score["joint"])

    def test_extra_prose_and_fields_fail_strict_format(self):
        target = {"category": "gpu_oom", "next_check": "inspect_gpu_memory"}
        self.assertFalse(
            score_answer("答案：" + json.dumps(target), target)["json_format"]
        )
        self.assertFalse(
            score_answer(json.dumps({**target, "why": "显存不足"}), target)["joint"]
        )

    def test_denominator_includes_failed_format(self):
        target = {"category": "gpu_oom", "next_check": "inspect_gpu_memory"}
        rows = [
            {"checks": score_answer(json.dumps(target), target)},
            {"checks": score_answer("not json", target)},
        ]
        self.assertEqual(summarize(rows)["rates"]["joint"], 0.5)


if __name__ == "__main__":
    unittest.main()
