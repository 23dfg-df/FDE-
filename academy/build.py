"""Build an offline FDE learning handbook using only the Python standard library."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = "2026.11.16-v2"
TRACK_FILES = ("engineering", "ai", "delivery")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def practice_blocks(text):
    """Parse the small, authored Markdown subset without accepting raw HTML."""
    lines = text.splitlines()
    blocks, index, heading_count = [], 0, 0

    def cells(line):
        return [value.strip() for value in line.strip().strip("|").split("|")]

    def table_start(position):
        return (position + 1 < len(lines) and lines[position].strip().startswith("|")
                and bool(re.fullmatch(r"\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?", lines[position + 1].strip())))

    def list_item(line):
        return re.match(r"^(?:(?P<bullet>[-*])|(?P<number>\d+)\.)\s+(?P<text>.+)$", line)

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("```"):
            language = line[3:].strip()
            index += 1
            code = []
            while index < len(lines) and lines[index].strip() != "```":
                code.append(lines[index]); index += 1
            if index == len(lines):
                raise ValueError("Unclosed practice code fence")
            blocks.append({"type": "code", "language": language, "text": "\n".join(code)})
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            heading_count += 1
            blocks.append({"type": "heading", "level": len(heading[1]), "text": heading[2],
                           "id": f"practice-section-{heading_count}"})
            index += 1
            continue
        if table_start(index):
            headers = cells(lines[index])
            index += 2
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                row = cells(lines[index])
                if len(row) != len(headers):
                    raise ValueError("Practice table column count does not match headers")
                rows.append(row); index += 1
            blocks.append({"type": "table", "headers": headers, "rows": rows})
            continue
        item = list_item(line)
        if item:
            ordered, items = bool(item["number"]), []
            while index < len(lines):
                item = list_item(lines[index].strip())
                if not item or bool(item["number"]) != ordered:
                    break
                items.append(item["text"]); index += 1
            blocks.append({"type": "list", "ordered": ordered, "items": items})
            continue
        paragraph = []
        while index < len(lines):
            current = lines[index].strip()
            if not current or re.match(r"^#{1,6}\s|^```", current) or list_item(current) or table_start(index):
                break
            paragraph.append(current); index += 1
        if not paragraph:
            raise ValueError("Unsupported practice Markdown at line " + str(index + 1))
        blocks.append({"type": "paragraph", "text": "\n".join(paragraph)})
    return blocks


def load_practice():
    practice = read_json(ROOT / "content/practice.json")
    source = (ROOT / "content/practice-plan.md").read_text("utf-8")
    practice["document"] = {"filename": "实践提升计划与验收标准.md", "markdown": source,
                            "blocks": practice_blocks(source)}
    return practice


def validate_practice(practice, lesson_ids):
    """Keep the published plan within the approved calendar and hour budget."""
    phases, advanced = practice["phases"], practice["advanced"]
    if len(phases) != 6 or sum(p["hours"] for p in phases) != 126:
        raise ValueError("Practice core phases must total 126 hours in six phases")
    if len(advanced) != 3 or sum(p["hours"] for p in advanced) != 240:
        raise ValueError("Advanced practice must total 240 hours in three phases")
    if len({p["id"] for p in phases}) != len(phases):
        raise ValueError("Practice phase ids must be unique")
    next_date = date(2026, 11, 16)
    for phase in phases:
        start, end = date.fromisoformat(phase["start"]), date.fromisoformat(phase["end"])
        if start != next_date or end < start:
            raise ValueError("Practice core phase dates must be consecutive")
        budget = sum(2 if start + timedelta(days=day) < date(2026, 12, 15) else 4
                     for day in range((end - start).days + 1))
        if phase["hours"] != budget or phase["level"] != "core":
            raise ValueError("Practice core phase budget does not match calendar")
        if not phase["lessons"] or any(ref not in lesson_ids for ref in phase["lessons"]):
            raise ValueError("Practice phase lesson references must exist")
        next_date = end + timedelta(days=1)
    if next_date != date(2027, 1, 1):
        raise ValueError("Practice core phases must end on 2026-12-31")
    for phase in advanced:
        start, end = date.fromisoformat(phase["start"]), date.fromisoformat(phase["end"])
        if start != next_date or (end - start).days != 27 or phase["hours"] != 80:
            raise ValueError("Advanced practice phases require consecutive four-week 80-hour blocks")
        next_date = end + timedelta(days=1)
    if next_date != date(2027, 3, 26):
        raise ValueError("Advanced practice phases must end on 2027-03-25")
    blocks = practice["document"]["blocks"]
    if not blocks or blocks[0].get("text") != practice["title"]:
        raise ValueError("Practice document title must match its structured plan")


def coverage_map(outline):
    mapping = {
        "s1-1": [["eng-01"], ["eng-01", "eng-08"], ["eng-01", "eng-02"], ["eng-02", "eng-05"], ["eng-03"], ["eng-02", "eng-11"]],
        "s1-2": [["eng-07"]] * 5,
        "s1-3": [["eng-03", "eng-09"], ["eng-09"], ["eng-09"], ["eng-09"], ["ops-07", "ops-08"]],
        "s1-4": [["eng-05", "eng-08"], ["eng-05"], ["eng-05", "eng-08"], ["eng-05"], ["eng-05", "eng-08"]],
        "s1-5": [["eng-04"], ["eng-04", "eng-10"], ["eng-10"], ["eng-10"]],
        "s1-6": [["eng-03"], ["eng-03", "eng-06"], ["eng-06", "eng-09"], ["ops-02", "ops-04"]],
        "s2-1": [["ai-01"], ["ai-01"], ["ai-01", "ai-05"], ["ai-03"], ["ai-02", "ops-10"]],
        "s2-2": [["ai-02"], ["ai-02"], ["ai-02", "ops-10"]],
        "s2-3": [["ai-01"], ["ai-01"], ["ai-08"], ["ai-01", "eng-02"], ["ai-06", "ai-08"]],
        "s2-4": [["ai-03"], ["ai-03"], ["ai-04"], ["ai-04", "ai-11"], ["ai-04"], ["ai-03", "ai-05", "ai-11"]],
        "s2-5": [["ai-05"], ["ai-05", "ai-06"], ["ai-05", "ai-11"]],
        "s2-6": [["ai-06", "ai-08"], ["ai-06", "ai-07"], ["ai-08", "eng-08"], ["ai-08"], ["ai-06", "ai-08"], ["ai-06", "ai-07"]],
        "s2-7": [["ai-07"], ["ai-07"], ["ai-07", "ai-12"], ["ai-07"]],
        "s2-8": [["ai-12"], ["ai-12"], ["ai-12"], ["ai-12", "ai-11", "ai-06"]],
        "s3-1": [["ops-06", "ops-07"], ["ops-06", "ops-07"], ["ops-07"], ["ops-07"], ["ops-07", "ops-10"]],
        "s3-2": [["ops-03"], ["ops-03"], ["ops-08"], ["ops-03", "eng-11"], ["ops-08"]],
        "s3-3": [["ops-06"], ["ops-09"], ["ops-09"], ["ops-09", "ops-10"], ["ops-06", "ops-12"], ["ops-01"], ["ops-01", "ops-07"], ["ops-10"], ["ops-01", "ops-10"], ["ops-07", "ops-09"], ["ops-01"], ["ops-12"], ["ops-04"], ["ops-12", "ai-05"], ["ops-12"], ["ops-12"]],
        "s4-1": [["ops-05"], ["ops-05"], ["ops-05", "ops-11"], ["ops-11"]],
        "s4-2": [["ops-05"], ["ops-05"], ["ops-05", "ops-11"], ["ops-11", "ai-02"]],
        "s4-3": [["ops-05", "ops-11"], ["ops-11"], ["ops-11"], ["ops-04", "ops-11"]],
        "s4-4": [["ops-10"], ["ops-08", "ops-10"], ["ops-10", "ops-11"], ["ops-10"]],
        "s4-5": [["ai-10"], ["ai-10"], ["ai-09", "ai-10"]],
    }
    result = []
    for module in outline["modules"]:
        rows = mapping[module["id"]]
        if len(rows) != len(module["topics"]):
            raise ValueError("Outline topic count drift: " + module["id"])
        for index, (topic, ids) in enumerate(zip(module["topics"], rows), 1):
            result.append({"id": f"{module['id']}.{index:02}", "module": module["id"], "topic": topic, "lessons": ids})
    return result


def advanced_weeks():
    pairs = [
        (["eng-07", "eng-08"], "算法与并发", "用边界输入比较两种实现，记录复杂度与取消行为。"),
        (["eng-09", "eng-10"], "网络与数据可靠性", "复现一条连接故障和一次缓存陈旧问题，写排查路径。"),
        (["eng-11", "eng-12"], "工程质量与源码复现", "在隔离分支提交一个小改动，保留测试和回滚方法。"),
        (["ai-07", "ai-08"], "工具接口与任务恢复", "实现一个只读工具，验证参数错误、权限不足和重试路径。"),
        (["ai-09", "ai-10"], "训练与模型变更评估", "先完成小模型重载预测；再写微调实验的数据与验收计划。"),
        (["ai-11", "ai-12"], "开源知识库与研发协作", "选一页DocLens结果接入知识库，记录版本和可追溯引用。"),
        (["ops-07"], "云与网络拓扑", "画出同一应用的云上和内网拓扑，标注数据与信任边界。"),
        (["ops-08"], "编排与发布", "验证一组部署清单和回滚步骤；环境不足时标为未实跑。"),
        (["ops-09"], "离线交付", "制作依赖清单与校验包，在隔离目录验证恢复流程。"),
        (["ops-10"], "容量与成本", "把真实测量和假设分开，提交可调整参数的容量方案。"),
        (["ops-11"], "推理与压测", "预约共享资源后完成有界小并发对照，保留失败和原始记录。"),
        (["ops-12"], "演示、复盘与知识转移", "按验收矩阵演示全链路，让另一位同学照手册重做一个任务。"),
    ]
    start = date(2027, 1, 1)
    return [{"title": title, "lessons": ids, "practice": practice,
             "dates": f"{start + timedelta(days=i * 7)} — {start + timedelta(days=i * 7 + 6)}"}
            for i, (ids, title, practice) in enumerate(pairs)]


def validate(data):
    errors = []
    lessons = data["lessons"]
    ids = [x["id"] for x in lessons]
    source_ids = [s["id"] for s in data["sources"]]
    if len(ids) != 36 or len(set(ids)) != len(ids): errors.append("Expected 36 unique lessons")
    if len(set(source_ids)) != len(source_ids): errors.append("Duplicate source ids")
    if sum(x["level"] == "core" for x in lessons) != 18: errors.append("Expected 18 core lessons")
    if sum(x["hours"] for x in lessons if x["level"] == "core") != 108: errors.append("Core hours must total 108")
    if len(data["coverage"]) != 110: errors.append("Expected all 110 original topics")
    for s in data["sources"]:
        for key in ("id", "title", "url", "kind", "checked", "license", "use", "reading", "reproduction", "limits"):
            if not isinstance(s.get(key), str) or not s[key].strip(): errors.append(f"Missing source field {s.get('id')}.{key}")
        if not s.get("url", "").startswith("https://"): errors.append("Source must use HTTPS: " + s["id"])
    for lesson in lessons:
        lid = lesson["id"]
        if lesson["level"] not in ("core", "advanced"): errors.append(lid + " invalid level")
        if len(lesson["sections"]) < 4 or len(lesson["quiz"]) < 2: errors.append(lid + " insufficient explanation or assessment")
        body = "".join(s["body"] for s in lesson["sections"])
        if len(re.findall(r"[\u4e00-\u9fff]", body)) < 700: errors.append(lid + " explanation too brief")
        for ref in lesson["prerequisites"]:
            if ref not in ids or ref == lid: errors.append(lid + " invalid prerequisite " + ref)
        for ref in lesson["sources"]:
            if ref not in source_ids: errors.append(lid + " invalid source " + ref)
        if not lesson["sources"]: errors.append(lid + " requires sources")
        if lesson.get("lab") and not (ROOT / lesson["lab"]).is_file(): errors.append(lid + " lab missing")
        for q in lesson["quiz"]:
            if type(q["answer"]) is not int or not 0 <= q["answer"] < len(q["options"]): errors.append(lid + " invalid quiz answer")
        for key in ("task", "steps", "hints", "solution", "acceptance", "deliverable"):
            if not lesson["exercise"].get(key): errors.append(lid + " missing exercise " + key)
        if "\\n" in lesson["example"]["code"] and "\n" not in lesson["example"]["code"]: errors.append(lid + " example has literal newlines only")
    graph = {l["id"]: l["prerequisites"] for l in lessons}
    def visit(node, active, done):
        if node in active: raise ValueError("Prerequisite cycle: " + node)
        if node in done: return
        active.add(node)
        for parent in graph[node]: visit(parent, active, done)
        active.remove(node); done.add(node)
    try:
        done = set()
        for lid in ids: visit(lid, set(), done)
    except (ValueError, KeyError) as e: errors.append(str(e))
    for row in data["coverage"]:
        if not row["lessons"] or any(ref not in ids for ref in row["lessons"]): errors.append("Coverage has invalid references")
    try:
        validate_practice(data["practice"], ids)
    except (ValueError, KeyError, TypeError) as error:
        errors.append("Practice plan: " + str(error))
    if errors: raise ValueError("\n".join(errors))


def load_data():
    tracks, sources, lessons = [], [], []
    for filename in TRACK_FILES:
        chunk = read_json(ROOT / "content" / (filename + ".json"))
        tracks.append(chunk["track"]); sources.extend(chunk["sources"])
        for lesson in chunk["lessons"]: lessons.append({**lesson, "track": chunk["track"]["id"]})
    # Core lessons precede advanced lessons in the reader and schedule.
    lessons.sort(key=lambda l: (l["level"] != "core", TRACK_FILES.index(l["track"]), l["id"]))
    by_id = {l["id"]: l for l in lessons}
    for lid, parent in (("ai-01", "eng-03"), ("ops-01", "eng-06"), ("ai-07", "eng-09"), ("ops-08", "ops-03")):
        if parent not in by_id[lid]["prerequisites"]: by_id[lid]["prerequisites"].append(parent)
    outline = read_json(ROOT / "content/original-outline.json")
    templates = [{"filename": p.name, "title": p.read_text("utf-8").splitlines()[0].lstrip("# "), "content": p.read_text("utf-8")}
                 for p in sorted((ROOT / "templates").glob("*.md"))]
    data = {"version": VERSION, "checkedAt": "2026-11-16", "tracks": tracks, "sources": sources,
            "lessons": lessons, "outline": outline, "coverage": coverage_map(outline),
            "advancedWeeks": advanced_weeks(), "templates": templates,
            "projects": read_json(ROOT / "content/projects.json"), "practice": load_practice()}
    validate(data)
    return data


def markdown(lesson, source_map):
    lines = ["# " + lesson["title"], "", f"编号：{lesson['id']} · {'年底核心' if lesson['level']=='core' else '进阶实践'} · 学习预算 {lesson['hours']} 小时", "", lesson["summary"], "", "## 学习目标", ""]
    lines.extend("- " + x for x in lesson["outcomes"])
    if lesson["prerequisites"]: lines += ["", "建议先修：" + "、".join(f"[{x}]({x}.md)" for x in lesson["prerequisites"])]
    for s in lesson["sections"]: lines += ["", "## " + s["title"], "", s["body"]]
    e = lesson["example"]
    lines += ["", "## " + e["title"], "", "```" + e["language"], e["code"], "```", "", e["explanation"]]
    if lesson.get("lab"): lines += ["", f"配套实验：[{lesson['lab']}](../{lesson['lab']})。请在解压包根目录按脚本说明运行。"]
    e = lesson["exercise"]
    lines += ["", "## 本课只做一个任务", "", e["task"], ""]
    lines += [f"{i}. {x}" for i, x in enumerate(e["steps"], 1)]
    lines += ["", "<details><summary>需要帮助时查看提示</summary>", ""] + ["- " + x for x in e["hints"]] + ["", "</details>"]
    lines += ["", "<details><summary>已经尝试或求助后查看参考解释</summary>", "", e["solution"], "", "</details>", "", "### 验收", ""] + ["- " + x for x in e["acceptance"]]
    lines += ["", "需要保存：" + e["deliverable"], "", "## 失败时检查", ""]
    for p in lesson["pitfalls"]: lines += ["### " + p["symptom"], "", "可能原因：" + p["cause"], "", "检查：" + p["check"], ""]
    lines += ["## 自测", ""]
    for i, q in enumerate(lesson["quiz"], 1):
        lines += [f"### {i}. {q['question']}", ""] + [f"- {chr(65+j)}. {option}" for j, option in enumerate(q["options"])]
        lines += ["", "<details><summary>提交自己的选择后查看解释</summary>", "", f"参考选项：{chr(65+q['answer'])}。{q['explanation']}", "", "</details>", ""]
    lines += ["## 证据记录", "", "- 实现证据：命令、输入、预期、实际结果、失败与未执行项。", "- 学习掌握证据：自己能够解释、独立重做或定位的问题；不能用助手完成替代。", "", "## 官方来源与延伸阅读", ""]
    for sid in lesson["sources"]:
        s = source_map[sid]
        lines += [f"- [{s['title']}]({s['url']})：{s['use']} 建议先读：{s['reading']}（核对 {s['checked']}）"]
    return "\n".join(lines) + "\n"


def build(output, docs=None):
    data = load_data()
    html = (ROOT / "web/index.html").read_text("utf-8")
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    replacements = {"/*__STYLES__*/": (ROOT / "web/styles.css").read_text("utf-8"), "__KNOWLEDGE__": serialized,
                    "/*__CORE__*/": (ROOT / "web/core.js").read_text("utf-8"), "/*__APP__*/": (ROOT / "web/app.js").read_text("utf-8")}
    for token, value in replacements.items():
        if html.count(token) != 1: raise ValueError("Unexpected template token count: " + token)
        html = html.replace(token, value)
    if re.search(r'<script[^>]+src=|<link[^>]+stylesheet|@import\s|url\(https?://', html): raise ValueError("Unexpected remote runtime dependency")
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(html, "utf-8")
    if docs:
        docs.mkdir(parents=True, exist_ok=True)
        sources = {s["id"]: s for s in data["sources"]}
        for l in data["lessons"]: (docs / (l["id"] + ".md")).write_text(markdown(l, sources), "utf-8")
        (docs / "PRACTICE.md").write_text(data["practice"]["document"]["markdown"], "utf-8")
        toc = ["# FDE 完整学习教程目录", "", "覆盖用户提供的22模块110知识点；覆盖入口不等于已经掌握。18核心+18进阶课程按需阅读，先练习再查看参考。", "", "先看 [实践提升计划与验收标准](PRACTICE.md)：年底126小时完成代码修改、故障排查与同学交付。课程参考课时包含在实践预算内，不重复叠加。", ""]
        for track in data["tracks"]:
            toc += ["## " + track["title"], "", track["description"], ""]
            for l in data["lessons"]:
                if l["track"] == track["id"]: toc += [f"- [{l['id']} {l['title']}]({l['id']}.md) · {l['hours']}小时 · {'核心' if l['level']=='core' else '进阶'}"]
            toc += [""]
        (docs / "README.md").write_text("\n".join(toc), "utf-8")
        source_text = ["# 开源项目与官方资料研究记录", "", "核对日期：2026-11-16。记录用途、源码阅读入口和最小复现范围；研究不等于所有项目已部署。", ""]
        for s in data["sources"]:
            source_text += ["## " + s["title"], "", f"[原始来源]({s['url']})", "", "- 借鉴：" + s["use"], "- 阅读入口：" + s["reading"], "- 最小复现：" + s["reproduction"], "- 边界：" + s["limits"], "- 许可：" + s["license"], ""]
        (docs / "SOURCES.md").write_text("\n".join(source_text), "utf-8")
        coverage = ["# 原大纲逐项映射", "", "110项全部保留；映射是课程覆盖入口，不是熟练度认证。", ""]
        for m in data["outline"]["modules"]:
            coverage += ["## " + m["id"] + " " + m["title"], ""]
            for row in data["coverage"]:
                if row["module"] == m["id"]: coverage += ["- " + row["topic"] + " → " + "、".join(f"[{x}]({x}.md)" for x in row["lessons"])]
            coverage += [""]
        (docs / "COVERAGE.md").write_text("\n".join(coverage), "utf-8")
    stats = {"version": VERSION, "lessons": len(data["lessons"]), "quizzes": sum(len(l["quiz"]) for l in data["lessons"]),
             "original_modules": 22, "mapped_topics": len(data["coverage"]), "sources": len(data["sources"]),
             "explanation_chinese_characters": sum(len(re.findall(r"[\u4e00-\u9fff]", s["body"])) for l in data["lessons"] for s in l["sections"]),
             "templates": len(data["templates"]), "core_hours": 108, "core_review_hours": 18, "advanced_lesson_hours": 144,
             "course_hours_scope": "reference_only_included_in_practice_budget_not_additional",
             "practice_hours": sum(p["hours"] for p in data["practice"]["phases"]),
             "advanced_practice_hours": sum(p["hours"] for p in data["practice"]["advanced"]),
             "html_bytes": output.stat().st_size, "html_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/index.html")
    parser.add_argument("--docs", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.docs), ensure_ascii=False, indent=2))
