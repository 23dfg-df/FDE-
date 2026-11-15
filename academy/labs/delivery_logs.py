"""离线结构化日志归组；duration为教学固定数据，不是实测性能。"""
import json
import math


def summarize(lines):
    requests, rejected = {}, []
    for number, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
            request_id = event["request_id"]
            duration = event["duration_ms"]
            if (not isinstance(request_id, str) or not request_id or
                    isinstance(duration, bool) or not isinstance(duration, (int, float)) or
                    not math.isfinite(duration) or duration < 0 or
                    not isinstance(event.get("stage"), str) or
                    not isinstance(event.get("status"), str)):
                raise ValueError("invalid event fields")
            requests.setdefault(request_id, []).append(event)
        except (ValueError, KeyError, TypeError):
            rejected.append(number)
    result = []
    for request_id, events in sorted(requests.items()):
        children = [e for e in events if e["stage"] != "request"]
        totals = [e for e in events if e["stage"] == "request"]
        result.append({"request_id": request_id,
                       "total_ms": totals[-1]["duration_ms"] if totals else None,
                       "longest_child": max(children, key=lambda x: x["duration_ms"])["stage"] if children else None,
                       "failed_stages": [e["stage"] for e in events if e["status"] == "error"],
                       "events": len(events)})
    return {"requests": result, "rejected_line_numbers": rejected,
            "scope": "synthetic_log_analysis_not_measured_latency"}


def demo():
    events = [
        {"request_id": "r-1", "stage": "retrieve", "duration_ms": 20, "status": "ok"},
        {"request_id": "r-2", "stage": "retrieve", "duration_ms": 18, "status": "ok"},
        {"request_id": "r-1", "stage": "model", "duration_ms": 1900, "status": "ok"},
        {"request_id": "r-2", "stage": "model", "duration_ms": 3000, "status": "error"},
        {"request_id": "r-1", "stage": "request", "duration_ms": 1950, "status": "ok"},
        {"request_id": "r-2", "stage": "request", "duration_ms": 3040, "status": "error"},
    ]
    return summarize([json.dumps(e) for e in events] + ["broken line"])


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
