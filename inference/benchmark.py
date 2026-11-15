"""同权重、同模板、同生成配置的真实服务对照；不重试或隐藏失败。"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import statistics
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

MODEL = "Qwen/Qwen2.5-3B-Instruct"
SYSTEM = "你是一名耐心的技术助教，请用简洁中文回答。"
PROMPT = "请用简洁中文解释 GPU 推理、KV 缓存和连续批处理各自的作用。"
MAX_TOKENS = 64


def request_spec(engine: str, stream: bool) -> tuple[str, dict[str, Any]]:
    if engine == "transformers":
        return (
            "http://127.0.0.1:18123/generate" + ("/stream" if stream else ""),
            {"prompt": PROMPT, "max_new_tokens": MAX_TOKENS},
        )
    return (
        "http://127.0.0.1:18301/v1/chat/completions",
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": PROMPT},
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": 0,
            "top_p": 1,
            "repetition_penalty": 1.05,
            "stop_token_ids": [151645, 151643],
            "seed": 42,
            "stream": stream,
            **({"stream_options": {"include_usage": True}} if stream else {}),
        },
    )


def make_request(
    engine: str, stream: bool = False, barrier: Any = None
) -> dict[str, Any]:
    url, payload = request_spec(engine, stream)
    record: dict[str, Any] = {"engine": engine, "stream": stream, "request": payload}
    # Connect independently; client construction is not model latency.
    with httpx.Client(timeout=120, trust_env=False) as client:
        if barrier is not None:
            barrier.wait(timeout=30)
        started = time.perf_counter()
        try:
            if not stream:
                response = client.post(url, json=payload)
                record["http_status"] = response.status_code
                record["response"] = response.json()
                record["ok"] = response.is_success
            else:
                events = []
                answer = ""
                final = None
                first_content = None
                done_marker = False
                event_name = "message"
                with client.stream("POST", url, json=payload) as response:
                    record["http_status"] = response.status_code
                    if not response.is_success:
                        record["response"] = json.loads(response.read())
                    else:
                        for line in response.iter_lines():
                            if line.startswith("event:"):
                                event_name = line[6:].strip()
                            if not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            elapsed = time.perf_counter() - started
                            if data == "[DONE]":
                                done_marker = True
                                events.append(
                                    {"event": "done_marker", "arrival_seconds": elapsed}
                                )
                                break
                            item = json.loads(data)
                            events.append(
                                {
                                    "event": event_name,
                                    "arrival_seconds": elapsed,
                                    "data": item,
                                }
                            )
                            delta = ""
                            if engine == "transformers":
                                if event_name == "token":
                                    delta = item.get("delta", "")
                                elif event_name == "done":
                                    final = item
                                elif event_name == "error":
                                    record["stream_error"] = item
                            else:
                                choices = item.get("choices", [])
                                if choices:
                                    delta = (
                                        choices[0].get("delta", {}).get("content") or ""
                                    )
                                    if choices[0].get("finish_reason"):
                                        record["finish_reason"] = choices[0][
                                            "finish_reason"
                                        ]
                                if item.get("usage"):
                                    final = {"usage": item["usage"]}
                            if delta:
                                if first_content is None:
                                    first_content = elapsed
                                answer += delta
                record["events"] = events
                record["answer"] = answer
                record["stream_answer"] = answer
                record["client_first_content_seconds"] = first_content
                record["response"] = final or record.get("response", {})
                record["ok"] = (
                    response.is_success
                    and final is not None
                    and "stream_error" not in record
                )
                if engine == "vllm" and not done_marker:
                    record["ok"] = False
                    record["stream_error"] = {"detail": "missing terminal [DONE]"}
            record["wall_seconds"] = time.perf_counter() - started
        except Exception as error:
            record.update(
                ok=False,
                error=f"{type(error).__name__}: {error}",
                wall_seconds=time.perf_counter() - started,
            )
    body = record.get("response", {})
    if record["ok"]:
        if engine == "transformers":
            record["input_tokens"] = body["input_tokens"]
            record["output_tokens"] = body["output_tokens"]
            record["model_generation_seconds"] = body["elapsed_seconds"]
            record["model_first_token_seconds"] = body.get("ttft_seconds")
            record["answer"] = body["answer"]
        else:
            record["input_tokens"] = body["usage"]["prompt_tokens"]
            record["output_tokens"] = body["usage"]["completion_tokens"]
            if not stream:
                record["answer"] = body["choices"][0]["message"]["content"]
                record["finish_reason"] = body["choices"][0]["finish_reason"]
    return record


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def summarize(runs: list[dict[str, Any]], wall: float) -> dict[str, Any]:
    successes = [run for run in runs if run["ok"]]
    latencies = [run["wall_seconds"] for run in successes]
    output_tokens = sum(run.get("output_tokens", 0) for run in successes)
    return {
        "requested": len(runs),
        "succeeded": len(successes),
        "failed": len(runs) - len(successes),
        "http_429": sum(run.get("http_status") == 429 for run in runs),
        "wall_seconds": wall,
        "successful_output_tokens": output_tokens,
        "aggregate_output_tokens_per_second": output_tokens / wall if wall else 0,
        "successful_requests_per_second": len(successes) / wall if wall else 0,
        "p50_success_wall_seconds": percentile(latencies, 0.5),
        "p95_success_wall_seconds": percentile(latencies, 0.95),
        "mean_success_wall_seconds": statistics.mean(latencies) if latencies else None,
    }


def concurrent_run(engine: str, concurrency: int, count: int = 8) -> dict[str, Any]:
    runs = []
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        # Synchronized waves produce actual simultaneous requests to both services.
        for offset in range(0, count, concurrency):
            width = min(concurrency, count - offset)
            barrier = threading.Barrier(width)
            futures = [
                pool.submit(make_request, engine, False, barrier) for _ in range(width)
            ]
            runs.extend(future.result() for future in futures)
    elapsed = time.perf_counter() - started
    return {
        "engine": engine,
        "concurrency": concurrency,
        "runs": runs,
        "summary": summarize(runs, elapsed),
    }


class GpuSampler:
    def __init__(self) -> None:
        self.samples: list[dict[str, Any]] = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.collect, daemon=True)

    def collect(self) -> None:
        while not self.stop.is_set():
            try:
                output = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=index,memory.used,memory.free,utilization.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    timeout=5,
                )
                self.samples.append(
                    {
                        "utc": datetime.now(timezone.utc).isoformat(),
                        "gpus": output.strip(),
                    }
                )
            except Exception as error:
                self.samples.append({"error": str(error)})
            self.stop.wait(0.25)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("evidence/inference/benchmark.json")
    )
    args = parser.parse_args()
    # 迁移后 18123 是同一 vLLM 实例的代理，不能继续标成两个推理引擎。
    with httpx.Client(timeout=5, trust_env=False) as client:
        health = client.get("http://127.0.0.1:18123/health")
        health.raise_for_status()
        if health.json().get("model") != MODEL:
            parser.error(
                "这是历史 Qwen 双引擎对照脚本；当前模型已迁移，"
                "18123 与 18301 共用混元实例。请使用 scripts/verify_hunyuan.py。"
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sampler = GpuSampler()
    sampler.thread.start()
    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "configuration": {
            "prompt": PROMPT,
            "system": SYSTEM,
            "max_tokens": MAX_TOKENS,
            "greedy": True,
            "repetition_penalty": 1.05,
        },
        "methodology": {
            "client_first_content_seconds": (
                "从客户端发出请求至第一个非空文本 SSE 增量，"
                "含排队/网络/解码缓冲，不等同服务器内部首 token。"
            ),
            "model_first_token_seconds": (
                "仅旧服务提供：模型 generate 开始至第一个生成 token，"
                "排除输入准备及网络。"
            ),
            "wall_seconds": (
                "客户端完整收到响应的耗时。并发组 wall 含各波间客户端创建与调度开销。"
            ),
            "throughput": (
                "并发组成功请求的真实输出 token 总数 / 整组 wall 秒，失败保留且不重试。"
            ),
            "percentiles": (
                "仅成功请求；每组 8 个请求，p95 是小样本描述，不作生产 SLA 结论。"
            ),
            "memory": (
                "nvidia-smi 板卡总占用采样，包含其他进程，"
                "不等同 PyTorch peak_allocated。"
            ),
            "hardware": (
                "同服务器两张 RTX 5090；旧服务 GPU 0，vLLM GPU 1；"
                "是部署栈对比，非严格隔离的内核性能研究。"
            ),
        },
        "warmups": [],
        "smoke": [],
        "streams": [],
        "loadtests": [],
    }

    def save() -> None:
        report["gpu_samples"] = sampler.samples
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    try:
        for engine in ("transformers", "vllm"):
            warmup = make_request(engine)
            report["warmups"].append(warmup)
            if not warmup["ok"]:
                save()
                raise RuntimeError(f"{engine} warmup failed: {warmup}")
            report["smoke"].append(make_request(engine))
            for _ in range(3):
                report["streams"].append(make_request(engine, stream=True))
            save()
            for concurrency in (1, 2, 4):
                result = concurrent_run(engine, concurrency)
                report["loadtests"].append(result)
                print(
                    json.dumps(
                        {
                            "engine": engine,
                            "concurrency": concurrency,
                            **result["summary"],
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                save()
    finally:
        sampler.stop.set()
        sampler.thread.join(timeout=6)
        save()
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    import os
    if os.getenv("FDE_ENABLE_LEGACY_QWEN") != "1":
        raise SystemExit("历史Qwen对照脚本：先准备匹配基座、18123代理和18301服务；确认后设置FDE_ENABLE_LEGACY_QWEN=1。不能用于当前混元比较。")
    main()
