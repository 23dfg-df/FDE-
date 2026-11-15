"""运行固定配置的开发集/保留测试集，并保存原始结果。"""

import argparse
import json
import time
from pathlib import Path

import httpx


def execute(url, output):
    client = httpx.Client(timeout=120, trust_env=False)
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    for split in ("dev", "test"):
        response = client.post(
            url + "/api/evaluation/start",
            json={"split": split, "limit": 50, "mode": "hybrid", "rerank": False},
        )
        response.raise_for_status()
        job_id = response.json()["id"]
        deadline, last = time.monotonic() + 1200, -1
        while time.monotonic() < deadline:
            response = client.get(url + "/api/evaluation/jobs/" + job_id)
            response.raise_for_status()
            job = response.json()
            if job["completed"] != last:
                print(
                    f"{split}: {job['completed']}/{job['total']} {job['status']}",
                    flush=True,
                )
                last = job["completed"]
            if job["status"] != "running":
                break
            time.sleep(1)
        else:
            raise TimeoutError("评测超过20分钟，请检查服务")
        (output / f"rag-{split}.json").write_text(
            json.dumps(job, ensure_ascii=False, indent=2), "utf-8"
        )
        reports.append(
            {"split": split, "status": job["status"], "summary": job.get("summary", {})}
        )
        if job["status"] != "completed":
            raise RuntimeError(f"评测未完成: {job}")
    exported = client.get(url + "/api/export").json()
    # 防止重复嵌套已有证据。
    exported.pop("evidence", None)
    (output / "project-records.json").write_text(
        json.dumps(exported, ensure_ascii=False, indent=2), "utf-8"
    )
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18300")
    parser.add_argument("--output", type=Path, default=Path("evidence"))
    args = parser.parse_args()
    execute(args.url, args.output)
