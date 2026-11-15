"""训练数据审计与明确限定范围的工单规则评测，不依赖 GPU。"""

import hashlib
import json
from collections import Counter
from pathlib import Path

LABELS = {
    "port_conflict": "inspect_listening_port",
    "gpu_oom": "inspect_gpu_memory",
    "connection_failed": "check_service_and_tunnel",
    "model_files_missing": "verify_model_path",
}
SYSTEM = (
    "将故障工单分类，只输出一个JSON对象，字段为category和next_check。"
    "category可选port_conflict、gpu_oom、connection_failed、model_files_missing。"
    "next_check可选inspect_listening_port、inspect_gpu_memory、check_service_and_tunnel、verify_model_path。"
    "不要输出解释或Markdown。"
)


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_data(directory):
    directory = Path(directory)
    groups, ids, prompts, families, hashes = {}, set(), set(), {}, {}
    for split, expected in (("train", 80), ("validation", 16), ("test", 20)):
        path = directory / f"{split}.jsonl"
        content = path.read_text("utf-8")
        hashes[path.name] = hashlib.sha256(content.encode()).hexdigest()
        rows = [json.loads(line) for line in content.splitlines() if line.strip()]
        if len(rows) != expected:
            raise ValueError(f"{split} 样本数应为 {expected}")
        families[split] = set()
        for row in rows:
            if (
                row.get("split") != split
                or row.get("provenance") != "synthetic_teaching_case"
            ):
                raise ValueError("数据划分或教学来源标记错误")
            if not isinstance(row.get("prompt"), str) or not row["prompt"].strip():
                raise ValueError("工单内容为空")
            normalized = "".join(row["prompt"].split())
            if row.get("id") in ids or normalized in prompts:
                raise ValueError("数据 ID 或问题跨划分重复")
            ids.add(row["id"])
            prompts.add(normalized)
            family = row.get("template_family")
            if not isinstance(family, str) or not family:
                raise ValueError("缺少模板家庭")
            families[split].add(family)
            target = row.get("target", {})
            if set(target) != {"category", "next_check"} or LABELS.get(
                target.get("category")
            ) != target.get("next_check"):
                raise ValueError("目标类别与动作映射错误")
        counts = Counter(row["target"]["category"] for row in rows)
        if any(counts[label] != expected // 4 for label in LABELS):
            raise ValueError("每个划分的四类数据必须均衡")
        groups[split] = rows
    for first, second in (
        ("train", "validation"),
        ("train", "test"),
        ("validation", "test"),
    ):
        if families[first] & families[second]:
            raise ValueError("模板家庭跨划分泄漏")
    return groups, {
        "counts": {key: len(value) for key, value in groups.items()},
        "file_sha256": hashes,
        "template_families": {key: sorted(value) for key, value in families.items()},
        "template_families_disjoint": True,
    }


def score_answer(answer, target):
    try:
        parsed = json.loads(answer.strip())
    except (ValueError, TypeError):
        parsed = None
    format_ok = (
        isinstance(parsed, dict)
        and set(parsed) == {"category", "next_check"}
        and all(isinstance(value, str) for value in parsed.values())
    )
    category_ok = (
        isinstance(parsed, dict) and parsed.get("category") == target["category"]
    )
    action_ok = (
        isinstance(parsed, dict) and parsed.get("next_check") == target["next_check"]
    )
    return {
        "json_format": format_ok,
        "category": category_ok,
        "next_check": action_ok,
        "joint": format_ok and category_ok and action_ok,
    }


def summarize(rows):
    if not rows:
        raise ValueError("不能汇总空评测")
    return {
        "count": len(rows),
        "passed": {
            key: sum(item["checks"][key] for item in rows)
            for key in ("json_format", "category", "next_check", "joint")
        },
        "rates": {
            key: sum(item["checks"][key] for item in rows) / len(rows)
            for key in ("json_format", "category", "next_check", "joint")
        },
        "scope": "synthetic_four_class_ticket_task_only",
    }
