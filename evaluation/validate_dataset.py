"""核对题库结构、开发/测试划分及参考证据；不评判模型答案质量。"""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    question_path = root / "evaluation/questions.json"
    manifest_path = root / "evaluation/corpus-manifest.json"
    try:
        payload = json.loads(question_path.read_text("utf-8"))
        manifest = json.loads(manifest_path.read_text("utf-8"))
    except (OSError, ValueError) as error:
        return {"status": "failed", "errors": [str(error)], "scope": "dataset_only"}
    questions = payload.get("questions", [])
    documents = manifest.get("documents", [])
    if not isinstance(questions, list) or not isinstance(documents, list):
        return {
            "status": "failed",
            "errors": ["questions/documents 必须是数组"],
            "scope": "dataset_only",
        }
    source_text: dict[str, str] = {}
    document_ids: set[str] = set()
    for doc in documents:
        name, doc_id = doc.get("filename", ""), doc.get("id", "")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9-]+\.md", name):
            errors.append(f"非法语料文件名: {name!r}")
            continue
        if name in source_text or not doc_id or doc_id in document_ids:
            errors.append(f"文档名称或 ID 重复: {name}")
        document_ids.add(doc_id)
        try:
            source_text[name] = (root / "corpus" / name).read_text("utf-8")
        except OSError as error:
            errors.append(f"文档缺失: {error}")
        if not doc.get("status") or not doc.get("provenance"):
            errors.append(f"文档缺少状态或依据: {name}")
    actual_files = {p.name for p in (root / "corpus").glob("*.md")}
    if actual_files != set(source_text):
        errors.append("corpus 中的 Markdown 文件与清单不一致")
    identifiers: set[str] = set()
    question_texts: set[str] = set()
    categories = {"normal", "multi_document", "unanswerable", "version_conflict"}
    counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    quotes_checked = 0
    for item in questions:
        if not isinstance(item, dict):
            errors.append("每道题必须是对象")
            continue
        item_id = item.get("id", "")
        if not isinstance(item_id, str) or not re.fullmatch(r"q\d{2}", item_id):
            errors.append(f"非法题目 ID: {item_id!r}")
        if item_id in identifiers:
            errors.append(f"重复题目 ID: {item_id}")
        identifiers.add(item_id)
        question = item.get("question", "")
        normalized = "".join(question.split()) if isinstance(question, str) else ""
        if not normalized or normalized in question_texts:
            errors.append(f"问题为空或跨划分重复: {item_id}")
        question_texts.add(normalized)
        split = item.get("split")
        category = item.get("category")
        if split not in {"dev", "test"}:
            errors.append(f"非法划分: {item_id}")
        else:
            counts[split] += 1
        if category not in categories:
            errors.append(f"非法题型: {item_id}")
        else:
            category_counts[category] += 1
        if not isinstance(item.get("answerable"), bool):
            errors.append(f"answerable 必须为布尔值: {item_id}")
        if item.get("answerable") != (category != "unanswerable"):
            errors.append(f"题型与 answerable 冲突: {item_id}")
        if not item.get("expected_answer") or not item.get("rubric"):
            errors.append(f"缺少参考答案或人工标准: {item_id}")
        sources = item.get("expected_sources", [])
        evidence = item.get("expected_evidence", [])
        if not isinstance(sources, list) or not isinstance(evidence, list):
            errors.append(f"来源和证据必须是数组: {item_id}")
            continue
        if len(sources) != len(set(sources)):
            errors.append(f"来源重复: {item_id}")
        if not item.get("answerable"):
            if sources or evidence:
                errors.append(f"无答案题不应配置支持虚构答案的证据: {item_id}")
        elif not sources or not evidence:
            errors.append(f"可回答题缺少证据: {item_id}")
        if category == "multi_document" and len(sources) < 2:
            errors.append(f"多文档题至少需要两份来源: {item_id}")
        evidence_sources = set()
        for quote_item in evidence:
            if not isinstance(quote_item, dict):
                errors.append(f"证据必须是对象: {item_id}")
                continue
            name, quote = quote_item.get("source"), quote_item.get("quote")
            evidence_sources.add(name)
            if name not in source_text:
                errors.append(f"未知证据来源: {item_id}: {name}")
            elif (
                not isinstance(quote, str)
                or not quote
                or quote not in source_text[name]
            ):
                errors.append(f"证据不是原文连续片段: {item_id}: {name}")
            else:
                quotes_checked += 1
        if set(sources) != evidence_sources:
            errors.append(f"来源列表与证据不一致: {item_id}")
    if len(questions) != 50 or counts != Counter({"dev": 30, "test": 20}):
        errors.append("本版本要求 50 题，开发集 30 题，测试集 20 题")
    for split in ("dev", "test"):
        split_categories = {
            q.get("category")
            for q in questions
            if isinstance(q, dict) and q.get("split") == split
        }
        if split_categories != categories:
            errors.append(f"{split} 未覆盖全部四种题型")
    return {
        "scope": "dataset_structure_and_literal_evidence_only",
        "status": "passed" if not errors else "failed",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": payload.get("dataset_id"),
        "document_count": len(source_text),
        "question_count": len(questions),
        "split_counts": dict(counts),
        "category_counts": dict(category_counts),
        "literal_quotes_checked": quotes_checked,
        "question_sha256": digest(question_path),
        "corpus_sha256": {
            name: hashlib.sha256(text.encode()).hexdigest()
            for name, text in source_text.items()
        },
        "errors": errors,
        "limitations": [
            "未运行模型，不包含任何回答准确率",
            "逐字证据检查不能自动证明答案与引用在语义上相符",
            "测试集与开发集共享语料，不能据此声称跨领域泛化",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
