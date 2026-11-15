"""固定开发题，比较检索配置。结果是来源/证据覆盖，不是回答正确率。"""

import argparse
import json
import statistics
import time
from pathlib import Path

import httpx


def run(base_url, split, limit):
    client = httpx.Client(timeout=180, trust_env=False)
    questions = client.get(base_url + "/api/evaluation/questions").json()["items"]
    selected = [x for x in questions if x["split"] == split and x["answerable"]][:limit]
    configurations = [
        ("bm25", False),
        ("dense", False),
        ("hybrid", False),
        ("hybrid", True),
    ]
    experiment = {
        "split": split,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "top_k": 5,
        "note": (
            "只评估可回答题的检索；无答案题另由问答评测处理。"
            "相同来源的错误章节不能算证据命中。"
        ),
        "configurations": [],
    }
    for mode, rerank in configurations:
        items = []
        for question in selected:
            response = client.post(
                base_url + "/api/retrieve",
                json={
                    "question": question["question"],
                    "mode": mode,
                    "rerank": rerank,
                    "top_k": 5,
                },
            )
            response.raise_for_status()
            result = response.json()
            chunks = result["chunks"]
            sources = {x["source"] for x in chunks}
            evidence = question["expected_evidence"]
            covered = sum(
                any(
                    x["source"] == e["source"] and e["quote"] in x["text"]
                    for x in chunks
                )
                for e in evidence
            )
            rank = next(
                (
                    i
                    for i, x in enumerate(chunks, 1)
                    if x["source"] in question["expected_sources"]
                ),
                None,
            )
            items.append(
                {
                    "question_id": question["id"],
                    "question": question["question"],
                    "all_sources_hit": set(question["expected_sources"]).issubset(
                        sources
                    ),
                    "evidence_covered": covered,
                    "evidence_count": len(evidence),
                    "first_source_rank": rank,
                    "result": result,
                }
            )
        n = len(items)
        experiment["configurations"].append(
            {
                "mode": mode,
                "rerank": rerank,
                "questions": n,
                "all_sources_hit_rate": sum(x["all_sources_hit"] for x in items) / n
                if n
                else None,
                "all_evidence_hit_rate": sum(
                    x["evidence_count"] == x["evidence_covered"] for x in items
                )
                / n
                if n
                else None,
                "source_mrr": sum(
                    1 / x["first_source_rank"] if x["first_source_rank"] else 0
                    for x in items
                )
                / n
                if n
                else None,
                "median_seconds": statistics.median(
                    x["result"]["timings"]["total_seconds"] for x in items
                )
                if n
                else None,
                "items": items,
            }
        )
    return experiment


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18300")
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument(
        "--output", type=Path, default=Path("evidence/retrieval-ablation.json")
    )
    args = parser.parse_args()
    result = run(args.url, args.split, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(
        json.dumps(
            [
                {k: v for k, v in x.items() if k != "items"}
                for x in result["configurations"]
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
