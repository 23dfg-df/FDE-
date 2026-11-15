"""混元迁移：当前服务发现、模板计数一致和旧 LoRA 拒绝路径。"""

import json
import sys
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from backend.config import DEFAULT_MODEL_NAME, Settings
from backend.main import create_app
from backend.repository import Repository
from backend.services import LEGACY_ADAPTER_BASE, Service, parse_triage_answer
from fastapi.testclient import TestClient


class Tokenizer:
    def __init__(self):
        self.calls = []

    def apply_chat_template(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return list(range(32))


class SimpleIndex:
    version = "fixed-index-version"
    chunks = [{"id": "one", "source": "guide.md", "text": "基线端口为18123。"}]

    def documents(self):
        return [{"id": "guide.md"}]

    def retrieve(self, *args):
        return {"chunks": self.chunks, "index_version": self.version}


def make_service(tmp_path, handler, model_name=DEFAULT_MODEL_NAME):
    settings = Settings(
        tmp_path,
        tmp_path / "data",
        tmp_path / "embedding",
        tmp_path / "reranker",
        model_name=model_name,
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = Service(
        settings,
        Repository(settings.data),
        SimpleIndex(),
        client=client,
        tokenizer=Tokenizer(),
    )
    return service, client


def catalogue(*names):
    return {"object": "list", "data": [{"id": name} for name in names]}


def completion(model, content):
    return {
        "model": model,
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 32, "completion_tokens": 16},
    }


def test_defaults_use_hunyuan_and_matching_tokenizer(monkeypatch):
    monkeypatch.delenv("CAPSTONE_MODEL_NAME", raising=False)
    monkeypatch.delenv("CAPSTONE_TOKENIZER", raising=False)
    settings = Settings.load()
    assert settings.model_name == "tencent/Hunyuan-1.8B-Instruct"
    assert settings.tokenizer_path == (
        settings.root.parent / "models/Hunyuan-1.8B-Instruct"
    )


def test_tokenizer_fallback_does_not_require_deleted_qwen(tmp_path, monkeypatch):
    loaded = []

    class AutoTokenizer:
        @staticmethod
        def from_pretrained(path, **kwargs):
            loaded.append((path, kwargs))
            return Tokenizer()

    monkeypatch.setitem(
        sys.modules, "transformers", SimpleNamespace(AutoTokenizer=AutoTokenizer)
    )
    settings = Settings(tmp_path, tmp_path / "data", tmp_path / "e", tmp_path / "r")
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200)))
    try:
        Service(settings, Repository(settings.data), SimpleIndex(), client=client)
    finally:
        client.close()
    assert loaded[0][0] == tmp_path.parent / "models/Hunyuan-1.8B-Instruct"
    assert loaded[0][1]["local_files_only"] is True


def test_availability_refreshes_and_requires_configured_model(tmp_path):
    names = [LEGACY_ADAPTER_BASE, "incident-triage"]
    service, client = make_service(
        tmp_path, lambda _: httpx.Response(200, json=catalogue(*names))
    )
    with client:
        first = service.model_availability()
        assert first["model_service_available"] is True
        assert first["model_ready"] is False
        assert first["adapter_availability"]["available"] is False
        assert first["adapter_availability"]["reason_code"] == "incompatible_base"
        names[:] = [DEFAULT_MODEL_NAME]
        second = service.model_availability()
        assert second["model_ready"] is True
        assert second["model_migration"]["status"] == "ready"
        assert second["adapter_availability"]["listed"] is False
        assert second["available_models"] == [DEFAULT_MODEL_NAME]


@pytest.mark.parametrize("payload", [{}, {"data": "bad"}, {"data": [None]}])
def test_malformed_catalogue_is_not_ready(tmp_path, payload):
    service, client = make_service(
        tmp_path, lambda _: httpx.Response(200, json=payload)
    )
    with client:
        result = service.model_availability()
    assert result["model_service_available"] is False
    assert result["model_ready"] is False
    assert result["adapter_availability"]["reason_code"] == "service_unavailable"


def test_old_adapter_rejected_with_409_before_generation(tmp_path):
    requests = []

    def handler(request):
        requests.append(request.method)
        return httpx.Response(
            200, json=catalogue(DEFAULT_MODEL_NAME, "incident-triage")
        )

    service, client = make_service(tmp_path, handler)
    with client, TestClient(create_app(service.settings, service)) as api:
        result = api.post(
            "/api/triage", json={"text": "GPU OOM", "model": "incident-triage"}
        )
    assert result.status_code == 409
    assert result.json()["code"] == "incompatible_base"
    assert "Qwen" in result.json()["detail"]
    assert requests == ["GET"], "不能把旧 Qwen LoRA 请求发送给混元"


def test_adapter_service_outage_is_503(tmp_path):
    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    service, client = make_service(tmp_path, handler)
    with client, TestClient(create_app(service.settings, service)) as api:
        result = api.post(
            "/api/triage", json={"text": "GPU OOM", "model": "incident-triage"}
        )
    assert result.status_code == 503
    assert result.json()["code"] == "service_unavailable"


def test_missing_compatible_adapter_is_503(tmp_path):
    service, client = make_service(
        tmp_path,
        lambda _: httpx.Response(200, json=catalogue(LEGACY_ADAPTER_BASE)),
        model_name=LEGACY_ADAPTER_BASE,
    )
    with client, TestClient(create_app(service.settings, service)) as api:
        result = api.post(
            "/api/triage", json={"text": "GPU OOM", "model": "incident-triage"}
        )
    assert result.status_code == 503
    assert result.json()["code"] == "not_deployed"


@pytest.mark.parametrize("wrapped", [False, True])
def test_base_triage_defaults_to_hunyuan_and_disables_thinking(tmp_path, wrapped):
    generated = []
    answer = '{"category":"gpu_oom","next_check":"inspect_gpu_memory"}'
    raw = f"<answer>\n{answer}\n</answer>" if wrapped else answer

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=catalogue(DEFAULT_MODEL_NAME))
        body = json.loads(request.content)
        generated.append(body)
        return httpx.Response(
            200,
            json=completion(
                DEFAULT_MODEL_NAME,
                raw,
            ),
        )

    service, client = make_service(tmp_path, handler)
    with client, TestClient(create_app(service.settings, service)) as api:
        result = api.post("/api/triage", json={"text": "CUDA out of memory"})
    assert result.status_code == 200
    assert result.json()["model"] == DEFAULT_MODEL_NAME
    assert generated[0]["model"] == DEFAULT_MODEL_NAME
    assert generated[0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert service.tokenizer.calls[-1][1]["enable_thinking"] is False
    assert result.json()["thinking_enabled"] is False
    assert result.json()["answer"] == raw
    assert result.json()["raw_model_answer"] == raw
    assert result.json()["parsed"]["category"] == "gpu_oom"
    assert result.json()["labels_consistent"] is True
    assert result.json()["parse_normalization"] == (
        "complete_answer_wrapper_removed" if wrapped else "none"
    )


@pytest.mark.parametrize(
    "raw",
    [
        '<answer>{"category":"gpu_oom","next_check":"inspect_gpu_memory"}',
        '{"category":"gpu_oom","next_check":"inspect_gpu_memory"}</answer>',
        '<answer>{"category":"gpu_oom","next_check":"inspect_gpu_memory"}</answer>suffix',
        'prefix<answer>{"category":"gpu_oom","next_check":"inspect_gpu_memory"}</answer>',
        '<think>推理</think><answer>{"category":"gpu_oom","next_check":"inspect_gpu_memory"}</answer>',
        '<answer><think>推理</think>{"category":"gpu_oom","next_check":"inspect_gpu_memory"}</answer>',
        '<answer><answer>{"category":"gpu_oom","next_check":"inspect_gpu_memory"}</answer></answer>',
        '<wrapper>{"category":"gpu_oom","next_check":"inspect_gpu_memory"}</wrapper>',
        "<answer>模型没有返回 JSON</answer>",
        '解释：{"category":"gpu_oom","next_check":"inspect_gpu_memory"}',
        "not json",
    ],
)
def test_triage_never_extracts_json_from_partial_or_arbitrary_envelope(raw):
    result = parse_triage_answer(raw, {"gpu_oom": "inspect_gpu_memory"})
    assert result["parsed"] is None
    assert result["labels_consistent"] is False


def test_rag_template_count_and_request_use_same_thinking_mode(tmp_path):
    sent = []

    def handler(request):
        body = json.loads(request.content)
        sent.append(body)
        return httpx.Response(
            200,
            json=completion(
                DEFAULT_MODEL_NAME,
                '{"supported":true,"answer":"18123","sources":["S1"]}',
            ),
        )

    service, client = make_service(tmp_path, handler)
    with client:
        result = service.ask("基线端口是多少？")
    assert service.tokenizer.calls[-1][1] == {
        "tokenize": True,
        "add_generation_prompt": True,
        "enable_thinking": False,
    }
    assert sent[0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert sent[0]["model"] == DEFAULT_MODEL_NAME
    assert result["generation"]["model"] == DEFAULT_MODEL_NAME
    assert result["generation"]["thinking_enabled"] is False
    assert result["human_verified"] is False


def test_history_is_preserved_across_model_configuration_change(tmp_path):
    service, client = make_service(
        tmp_path, lambda _: httpx.Response(200, json=catalogue(DEFAULT_MODEL_NAME))
    )
    historical = service.repository.save(
        "ask", {"generation": {"model": LEGACY_ADAPTER_BASE}, "answer": "历史结果"}
    )
    with client:
        service.settings = replace(service.settings, model_name=DEFAULT_MODEL_NAME)
        service.model_availability()
    assert service.repository.list()[0] == historical
