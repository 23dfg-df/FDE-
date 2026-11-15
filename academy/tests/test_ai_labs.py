import importlib.util
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "labs" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


retrieval, tools, training = [module(name) for name in ["ai_retrieval", "ai_tools", "ai_training"]]


class RetrievalTests(unittest.TestCase):
    def test_rank_and_unknown(self):
        docs = {"a": "transaction rollback", "b": "gpu memory"}
        self.assertEqual(retrieval.search(docs, "rollback")[0]["id"], "a")
        self.assertEqual(retrieval.search(docs, "missing"), [])
        self.assertEqual(retrieval.search({}, "rollback"), [])

    def test_metrics_do_not_count_duplicate_hits(self):
        self.assertEqual(retrieval.retrieval_metrics(["x", "a", "a"], ["a", "b"]), {"recall": 0.5, "reciprocal_rank": 0.5})

    def test_no_answer_uses_separate_evaluation(self):
        with self.assertRaises(ValueError):
            retrieval.retrieval_metrics([], [])


class ToolTests(unittest.TestCase):
    def test_replay_and_mutation_isolation(self):
        runner = tools.ToolRunner()
        result = runner.call("learner-a", "r1", "read_job", {"job_id": "job-a"})
        result["status"] = "tampered"
        self.assertEqual(runner.call("learner-a", "r1", "read_job", {"job_id": "job-a"})["status"], "completed")
        self.assertEqual(runner.executions, 1)

    def test_reject_cross_owner_and_unsupported_tool(self):
        runner = tools.ToolRunner()
        for name, arguments in [("read_job", {"job_id": "job-b"}), ("delete_job", {"job_id": "job-a"}), ("read_job", {"job_id": "job-a", "owner": "learner-b"})]:
            with self.assertRaises(tools.ToolError):
                runner.call("learner-a", "r1", name, arguments)
        self.assertEqual(runner.executions, 0)

    def test_request_identity_conflict(self):
        runner = tools.ToolRunner()
        runner.jobs["job-c"] = {"owner": "learner-a", "status": "queued"}
        runner.call("learner-a", "same", "read_job", {"job_id": "job-a"})
        with self.assertRaises(tools.ToolError):
            runner.call("learner-a", "same", "read_job", {"job_id": "job-c"})


class TrainingTests(unittest.TestCase):
    def test_new_process_loads_saved_model(self):
        model, _ = training.train(training.dataset(-20, 21), training.dataset(21, 31))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.json"
            path.write_text(json.dumps(model), encoding="utf-8")
            run = subprocess.run([sys.executable, str(ROOT / "labs/ai_training.py"),
                                  "--predict-model", str(path)], capture_output=True,
                                 text=True, check=True, timeout=15)
            self.assertEqual(json.loads(run.stdout),
                             [training.predict(model, x) for x, _ in training.dataset(31, 41)])

    def test_learning_and_reload(self):
        train = training.dataset(-20, 21)
        model, history = training.train(train, training.dataset(21, 31))
        self.assertLess(history[-1]["train_mse"], history[0]["train_mse"])
        self.assertLess(training.mse(model, training.dataset(31, 41)), 0.02)
        restored = json.loads(json.dumps(model))
        self.assertEqual([training.predict(model, x) for x, _ in train], [training.predict(restored, x) for x, _ in train])

    def test_normalization_fits_training_only(self):
        train = training.dataset(-20, 21)
        first, _ = training.train(train, training.dataset(21, 31))
        shifted, _ = training.train(train, training.dataset(100, 105))
        self.assertEqual((first["mean"], first["scale"]), (shifted["mean"], shifted["scale"]))
        tampered = dict(first, mean=first["mean"] + 1)
        self.assertNotEqual(training.predict(first, 1), training.predict(tampered, 1))


if __name__ == "__main__":
    unittest.main()
