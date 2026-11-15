"""交付审查回归：恢复失败不得删除原数据，离线资料不可突破脚本边界。"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def script_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_restore_rename_failure_preserves_original_data(tmp_path, monkeypatch):
    ops = script_module("ops")
    data = tmp_path / "data"
    data.mkdir()
    original = data / "valuable.md"
    original.write_text("需要保留的当前运行资料", "utf-8")
    saved = tmp_path / "backups" / "known-good"
    (saved / "data").mkdir(parents=True)
    (saved / "data" / "old.md").write_text("旧版本", "utf-8")
    (saved / "manifest.json").write_text(
        json.dumps({"id": "known-good", "files": ops.hashes(saved)}), "utf-8"
    )
    monkeypatch.setattr(ops, "ROOT", tmp_path)
    monkeypatch.setattr(
        ops, "run", lambda *args: "active" if args[-2:-1] == ("is-active",) else ""
    )
    monkeypatch.setattr(ops, "is_active", lambda: True)
    monkeypatch.setattr(ops, "backup", lambda: {"id": "safety"})
    original_rename = Path.rename

    def refuse_rename(path, target):
        if path == data:
            raise PermissionError("模拟 data 目录重命名失败")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", refuse_rename)
    with pytest.raises(PermissionError):
        ops.restore("known-good")
    assert original.is_file(), "移动原目录失败时，不能删除仍在原路径的有效数据"
    assert original.read_text("utf-8") == "需要保留的当前运行资料"


def test_backup_preserves_inactive_service(tmp_path, monkeypatch):
    ops = script_module("ops")
    data = tmp_path / "data"
    data.mkdir()
    (data / "example.md").write_text("备份前服务已经停止", "utf-8")
    calls = []
    monkeypatch.setattr(ops, "ROOT", tmp_path)
    monkeypatch.setattr(ops, "is_active", lambda: False)
    monkeypatch.setattr(ops, "run", lambda *args: calls.append(args))
    manifest = ops.backup()
    assert not any("start" in args for args in calls)
    restored_file = tmp_path / "backups" / manifest["id"] / "data" / "example.md"
    assert restored_file.read_text("utf-8") == "备份前服务已经停止"


def test_offline_untrusted_document_cannot_end_script(tmp_path):
    offline = script_module("build_offline")
    payload = (
        '</script><script src="https://example.invalid/execute.js"></script><p>正文</p>'
    )
    snapshot = {
        "source": "test_fixture",
        "generated_at": "2026-11-15T00:00:00Z",
        "status": {},
        "documents": [{"id": "example.md", "text": payload}],
        "questions": [],
        "evidence": [],
        "history": [],
    }
    destination = tmp_path / "offline.html"
    report = offline.build(ROOT, destination, snapshot)
    html = destination.read_text("utf-8")
    assert payload not in html
    assert html.count("<script>") == 3
    assert "\\u003c/script>" in html
    assert report["external_scripts_or_styles"] == 0


def test_evidence_coverage_requires_quote_not_only_document():
    from backend.services import evaluate_rules

    question = {
        "answerable": True,
        "expected_sources": ["policy.md"],
        "expected_evidence": [{"source": "policy.md", "quote": "每天最多 2 小时。"}],
    }
    unrelated = {"source": "policy.md", "text": "另一段关于网络的说明。"}
    answer = {
        "supported": True,
        "retrieval": {"chunks": [unrelated]},
        "context_chunks": [unrelated],
        "citations": [unrelated],
    }
    checks = evaluate_rules(question, answer)
    assert checks["retrieved_all_expected_sources"] is True
    assert checks["retrieved_evidence_covered"] == 0
    assert checks["context_evidence_covered"] == 0
    assert checks["cited_evidence_covered"] == 0
    assert checks["semantic_correctness"] == "pending_human_review"
