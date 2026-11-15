"""切换前必须具备完整训练证据，并拒绝被修改的适配器。"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from validate_lora import validate_metadata


class AdapterPreflightTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.base = self.root / "base"
        self.adapter = self.root / "adapter"
        self.adapter.mkdir()
        self.config = {
            "peft_type": "LORA",
            "task_type": "CAUSAL_LM",
            "r": 8,
            "target_modules": ["q_proj", "v_proj"],
            "base_model_name_or_path": str(self.base),
            "bias": "none",
        }
        (self.adapter / "adapter_config.json").write_text(json.dumps(self.config))
        (self.adapter / "adapter_model.safetensors").write_bytes(
            b"metadata-test-fixture"
        )
        self.summary = {
            "status": "completed",
            "reload_all_answers_match": True,
            "adapter_sha256": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.adapter.iterdir()
            },
        }
        self.write_summary()

    def write_summary(self):
        (self.root / "summary.json").write_text(json.dumps(self.summary))

    def test_complete_matching_metadata_is_accepted(self):
        result = validate_metadata(self.adapter, self.base)
        self.assertEqual(result["status"], "compatible_metadata")

    def test_partial_training_is_rejected(self):
        self.summary["status"] = "running"
        self.write_summary()
        with self.assertRaisesRegex(ValueError, "尚未完成"):
            validate_metadata(self.adapter, self.base)

    def test_modified_weights_are_rejected(self):
        (self.adapter / "adapter_model.safetensors").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "哈希不一致"):
            validate_metadata(self.adapter, self.base)

    def test_wrong_base_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "基础模型路径"):
            validate_metadata(self.adapter, self.root / "other-model")

    def test_inconsistent_reload_is_rejected(self):
        self.summary["reload_all_answers_match"] = False
        self.write_summary()
        with self.assertRaisesRegex(ValueError, "独立重载回答不一致"):
            validate_metadata(self.adapter, self.base)


if __name__ == "__main__":
    unittest.main()
