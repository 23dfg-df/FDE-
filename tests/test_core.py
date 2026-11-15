"""验证引用约束、索引持久化和 API 边界，而非只镜像实现。"""

import json
from pathlib import Path

import pytest
from backend.config import Settings
from backend.indexing import Index, safe_name, split_document
from backend.repository import Repository
from backend.services import evaluate_rules, parse_answer


class FakeModels:
    def embed(self, texts, query=False):
        return [
            [float("显存" in text) + 0.1, float("端口" in text) + 0.1, 0.1]
            for text in texts
        ]

    def rerank(self, question, chunks):
        return chunks


def config(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "gpu.md").write_text("# GPU排障\n显存不足需要检查当前占用。\n", "utf-8")
    (corpus / "network.md").write_text("# 网络说明\n端口18300是知识库入口。\n", "utf-8")
    return Settings(tmp_path, tmp_path / "data", Path("embedding"), Path("reranker"))


def test_heading_and_long_chunk_preserve_source():
    chunks = split_document(
        "test.md", "# 标题\n" + "显存" * 500 + "\n## 第二节\n端口说明。"
    )
    assert all(len(x["text"]) <= 420 for x in chunks)
    assert chunks[-1]["title"] == "第二节"
    assert chunks[-1]["start_line"] == 3
    assert len({x["id"] for x in chunks}) == len(chunks)
    assert all(x["source"] == "test.md" for x in chunks)


@pytest.mark.parametrize(
    "name",
    ["../secret.md", "/tmp/file.md", "x/y.md", ".hidden.md", "test.exe", "a\\b.md"],
)
def test_upload_cannot_escape_documents(name):
    with pytest.raises(ValueError):
        safe_name(name)


def test_citations_cannot_be_fabricated():
    chunks = [{"id": "x", "source": "gpu.md", "text": "显存"}]
    valid = parse_answer(
        json.dumps({"answer": "检查显存", "supported": True, "sources": ["S1"]}), chunks
    )
    assert valid["supported"] and valid["citations"][0]["source"] == "gpu.md"
    assert valid["human_verified"] is False
    fabricated = parse_answer(
        json.dumps({"answer": "编造", "supported": True, "sources": ["S99"]}), chunks
    )
    assert fabricated["supported"] is False and fabricated["citations"] == []


@pytest.mark.parametrize(
    "text",
    [
        "不是JSON",
        "[]",
        '{"answer":null}',
        '{"answer":"x","supported":"true","sources":[]}',
    ],
)
def test_invalid_output_never_claims_grounding(text):
    assert parse_answer(text, [])["supported"] is False


def test_answerability_check_does_not_call_semantics_verified():
    question = {"answerable": True, "expected_sources": ["a.md", "b.md"]}
    answer = {
        "supported": True,
        "retrieval": {"chunks": [{"source": "a.md"}]},
        "citations": [{"source": "a.md"}],
    }
    result = evaluate_rules(question, answer)
    assert result["retrieved_all_expected_sources"] is False
    assert result["semantic_correctness"] == "pending_human_review"


def test_explicit_refusal_conflict_preserves_raw_claim_and_separate_scores():
    raw = json.dumps(
        {
            "answer": "无法回答。资料未提供午餐信息。",
            "supported": True,
            "sources": ["S1"],
        }
    )
    result = parse_answer(raw, [{"source": "unrelated.md", "text": "其他资料"}])
    assert result["supported"] is False
    assert result["citations"] == []
    assert result["model_supported"] is True
    assert result["raw_support"] is True
    assert result["model_sources"] == ["S1"]
    assert result["support_conflict"] is True
    assert result["support_normalization"] == "explicit_refusal_prefix_v1"
    checks = evaluate_rules({"answerable": False, "expected_sources": []}, result)
    assert checks["answerability_matches"] is True
    assert checks["model_answerability_matches"] is False
    assert checks["support_normalized"] is True
    assert checks["semantic_correctness"] == "pending_human_review"


@pytest.mark.parametrize(
    "answer",
    ["资料不足时应停止猜测。", "无法回答是正常的拒答状态。", "不能使用旧适配器。"],
)
def test_refusal_guard_does_not_change_supported_explanations(answer):
    raw = json.dumps({"answer": answer, "supported": True, "sources": ["S1"]})
    result = parse_answer(raw, [{"source": "policy.md", "text": answer}])
    assert result["supported"] is True
    assert result["support_conflict"] is False


@pytest.mark.parametrize("placeholder", ["", "[]", "{}", "null"])
def test_empty_answers_are_explicit_service_fallback(placeholder):
    result = parse_answer(
        json.dumps({"answer": placeholder, "supported": False, "sources": []}), []
    )
    assert result["response_fallback"] is True
    assert result["supported"] is False
    assert "资料" in result["answer"]
    assert result["human_verified"] is False


def test_triage_network_failure_is_reported_as_service_error():
    from types import SimpleNamespace

    import httpx
    from backend.services import ModelAvailabilityError, Service

    service = object.__new__(Service)
    service.settings = SimpleNamespace(model_url="http://model/v1", model_name="base")

    def unavailable(request):
        raise httpx.ConnectError("offline", request=request)

    with httpx.Client(transport=httpx.MockTransport(unavailable)) as client:
        service.client = client
        with pytest.raises(ModelAvailabilityError) as failure:
            service.triage("test")
        assert failure.value.status_code == 503
        assert failure.value.code == "base_model_unavailable"


def test_index_roundtrip_and_rebuild(tmp_path):
    settings = config(tmp_path)
    first = Index(settings, FakeModels())
    before = first.version
    for mode in ("bm25", "dense", "hybrid"):
        answer = first.retrieve("显存不足", mode=mode, top_k=2, rerank=False)
        assert answer["chunks"]
        assert answer["index_version"] == before
    second = Index(settings, FakeModels())
    assert second.version == before
    first.add("update.md", "# 更新\n最新的显存处理指南。")
    with pytest.raises(FileExistsError):
        first.add("update.md", "不能覆盖")
    assert first.version == before
    first.rebuild()
    assert first.version != before
    assert len(first.documents()) == 3
    assert (settings.data / "indexes" / (before + ".json")).is_file()
    assert "fusion" in (settings.data / "pipelines/hybrid.yaml").read_text()


def test_sqlite_backup_preserves_history(tmp_path):
    repository = Repository(tmp_path / "original")
    record = repository.save("ask", {"answer": "中文", "question": "例子"})
    target = tmp_path / "restored"
    target.mkdir()
    repository.backup(target / "history.sqlite3")
    restored = Repository(target)
    assert restored.list()[0] == record


@pytest.mark.parametrize("corruption", ["text", "vector", "invalid_json"])
def test_index_cache_corruption_is_rebuilt(tmp_path, corruption):
    settings = config(tmp_path)
    first = Index(settings, FakeModels())
    path = settings.data / "indexes" / f"{first.version}.json"
    value = json.loads(path.read_text("utf-8"))
    if corruption == "text":
        value["chunks"][0]["text"] = "损坏资料不能进入知识库"
    elif corruption == "vector":
        value["chunks"][0]["embedding"] = [float("nan")]
    path.write_text(
        "{bad" if corruption == "invalid_json" else json.dumps(value), "utf-8"
    )
    restored = Index(settings, FakeModels())
    assert restored.version == first.version
    assert restored.chunks == first.chunks
