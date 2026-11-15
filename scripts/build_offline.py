"""生成不依赖网络资源的单文件学习页；真实模型操作在离线页禁用。"""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


def read_json(path):
    return json.loads(path.read_text("utf-8"))


def collect_snapshot(root, api_url=None):
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "saved_local_files",
        "status": {},
        "documents": [],
        "history": [],
        "questions": [],
        "evidence": [],
    }
    for path in sorted((root / "corpus").glob("*.md")):
        text = path.read_text("utf-8")
        title = next(
            (line.lstrip("# ") for line in text.splitlines() if line.startswith("# ")),
            path.stem,
        )
        snapshot["documents"].append(
            {
                "id": path.name,
                "title": title,
                "text": text,
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    question_path = root / "evaluation/questions.json"
    if question_path.exists():
        questions = read_json(question_path)
        snapshot["questions"] = (
            questions.get("questions", []) if isinstance(questions, dict) else questions
        )
    for path in sorted((root / "evidence").rglob("*.json")):
        if path.stat().st_size <= 5_000_000:
            snapshot["evidence"].append(
                {
                    "name": str(path.relative_to(root / "evidence")),
                    "data": read_json(path),
                }
            )
    if api_url:
        snapshot["source"] = "server_snapshot"
        for key, route in [
            ("status", "status"),
            ("documents", "documents"),
            ("history", "history"),
            ("questions", "evaluation/questions"),
            ("evidence", "evidence"),
        ]:
            with urlopen(api_url.rstrip("/") + "/api/" + route, timeout=60) as response:
                value = json.load(response)
            snapshot[key] = value if key == "status" else value["items"]
    else:
        snapshot["status"] = {
            "documents_count": len(snapshot["documents"]),
            "model": "参阅保存的实验报告",
            "gpus": [],
            "index_version": "离线未采集",
        }
        for item in snapshot["evidence"]:
            value = item["data"]
            if (
                isinstance(value, dict)
                and "history" in value
                and isinstance(value["history"], list)
            ):
                snapshot["history"] = value["history"]
    return snapshot


def script_text(value):
    return value.replace("</script", "<\\/script").replace("</SCRIPT", "<\\/SCRIPT")


def build(root, destination, snapshot):
    html = (root / "web/index.html").read_text("utf-8")
    css = (root / "web/styles.css").read_text("utf-8")
    html, count = re.subn(
        r'<link rel="stylesheet" href="styles\.css">',
        lambda _: "<style>" + css + "</style>",
        html,
    )
    if count != 1:
        raise ValueError("预期一个 styles.css 引用")
    serialized = (
        json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    scripts = ["<script>window.CAPSTONE_OFFLINE=" + serialized + ";</script>"]
    for name in ("lessons.js", "app.js"):
        html, count = re.subn(
            r'<script src="' + re.escape(name) + r'"></script>', "", html
        )
        if count != 1:
            raise ValueError(f"预期一个 {name} 引用")
        scripts.append(
            "<script>"
            + script_text((root / "web" / name).read_text("utf-8"))
            + "</script>"
        )
    html = html.replace("</body>", "\n".join(scripts) + "\n</body>", 1)
    if re.search(r'<script\b[^>]*\bsrc\s*=|<link\b[^>]*\brel=["\']stylesheet', html):
        raise ValueError("离线 HTML 仍含外部脚本或样式")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, "utf-8")
    return {
        "path": str(destination),
        "bytes": destination.stat().st_size,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "documents": len(snapshot["documents"]),
        "questions": len(snapshot["questions"]),
        "evidence_reports": len(snapshot["evidence"]),
        "history_records": len(snapshot["history"]),
        "external_scripts_or_styles": 0,
        "snapshot_source": snapshot["source"],
        "file_browser_test": "not_run",
    }


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-url",
        help="可选：从运行服务采集真实状态和历史，例如 http://127.0.0.1:18300",
    )
    parser.add_argument(
        "--snapshot", type=Path, help="可选：使用预先保存的完整 snapshot JSON"
    )
    parser.add_argument(
        "--output", type=Path, default=root / "outputs/FDE完整项目-离线学习版.html"
    )
    args = parser.parse_args()
    snapshot = (
        read_json(args.snapshot)
        if args.snapshot
        else collect_snapshot(root, args.api_url)
    )
    report = build(root, args.output.resolve(), snapshot)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
