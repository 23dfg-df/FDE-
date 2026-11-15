"""公开快照不得冒充实测；启动脚本必须检查被选择的物理卡。"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_public_snapshot_stays_consistent_with_sanitized_sources():
    snapshot = json.loads((ROOT / "examples/public-snapshot.json").read_text())
    assert len(snapshot["documents"]) == 17
    for document in snapshot["documents"]:
        text = (ROOT / "corpus" / document["id"]).read_text()
        assert document["text"] == text
        assert document["sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert snapshot["questions"] == json.loads(
        (ROOT / "evaluation/questions.json").read_text()
    )["questions"]


def test_public_demo_has_no_real_history_or_fabricated_measurements():
    snapshot = json.loads((ROOT / "examples/public-snapshot.json").read_text())
    assert snapshot["source"] == "public_teaching_snapshot"
    assert snapshot["status"]["model_ready"] is False
    assert snapshot["status"]["gpus"] == []
    assert snapshot["evidence"] == []
    assert len(snapshot["history"]) == 1
    row = snapshot["history"][0]
    assert row["provenance"] == "synthetic_teaching_example_not_model_output"
    assert row["elapsed_seconds"] is None
    assert row["supported"] is None


@pytest.mark.parametrize("free_mib,should_start", [(8192, False), (16000, True)])
def test_startup_checks_selected_gpu_and_forwards_paths(tmp_path, free_mib, should_start):
    model = tmp_path / "model with spaces"
    model.mkdir()
    (model / "model.safetensors").write_text("test placeholder, not model weights")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    trace = tmp_path / "queried-gpu"
    nvidia = fake_bin / "nvidia-smi"
    nvidia.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$TRACE_PATH"\nprintf "%s\\n" "$FAKE_FREE"\n')
    vllm = fake_bin / "vllm"
    vllm.write_text('#!/bin/sh\nprintf "visible=%s\\n" "$CUDA_VISIBLE_DEVICES"\nprintf "%s\\n" "$@"\n')
    nvidia.chmod(0o755)
    vllm.chmod(0o755)
    result = subprocess.run(
        ["bash", str(ROOT / "inference/start-hunyuan.sh")],
        env={**os.environ, "PATH": str(fake_bin) + os.pathsep + os.environ["PATH"],
            "TRACE_PATH": str(trace), "FAKE_FREE": str(free_mib),
            "FDE_MODEL_PATH": str(model), "FDE_PHYSICAL_GPU": "1",
            "FDE_VLLM_BIN": str(vllm), "FDE_GPU_MEMORY_UTILIZATION": "0.25"},
        capture_output=True, text=True, timeout=10,
    )
    assert "--id=1" in trace.read_text()
    if should_start:
        assert result.returncode == 0, result.stderr
        assert "visible=1" in result.stdout
        assert str(model) in result.stdout.splitlines()
        assert "0.25" in result.stdout.splitlines()
        assert "127.0.0.1" in result.stdout.splitlines()
    else:
        assert result.returncode != 0
        assert "可用显存不足" in result.stderr
        assert "visible=" not in result.stdout


def test_historical_benchmark_cannot_run_by_default():
    environment = dict(os.environ)
    environment.pop("FDE_ENABLE_LEGACY_QWEN", None)
    import sys
    result = subprocess.run(
        [sys.executable, str(ROOT / "inference/benchmark.py")],
        env=environment, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "FDE_ENABLE_LEGACY_QWEN=1" in result.stderr
