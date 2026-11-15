"""生成明确虚构的工单分类教学数据，按叙述模板家庭划分。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABELS = {
    "port_conflict": "inspect_listening_port",
    "gpu_oom": "inspect_gpu_memory",
    "connection_failed": "check_service_and_tunnel",
    "model_files_missing": "verify_model_path",
}
SIGNALS = {
    "port_conflict": [
        "启动应用时报 Address already in use，无法绑定端口",
        "监听地址绑定失败，日志写着 EADDRINUSE",
        "服务没有启动起来，提示端口已被另一个进程占用",
        "同一地址已经存在监听者，新进程无法 bind",
        "第二个服务启动时报告目标端口正在使用",
    ],
    "gpu_oom": [
        "加载模型时报 CUDA out of memory，申请显存失败",
        "生成回答中断，提示 GPU 显存不足",
        "张量无法分配到显卡，报 cudaErrorMemoryAllocation",
        "推理进程申请显存失败，错误类型是 OutOfMemoryError",
        "模型计算期间显卡内存不够，CUDA 分配失败",
    ],
    "connection_failed": [
        "客户端请求失败，返回 Connection refused",
        "电脑端无法连到服务器本地服务，提示连接被拒绝",
        "HTTP 请求没有建立连接，端口拒绝访问",
        "浏览器访问转发端口失败，报 ERR_CONNECTION_REFUSED",
        "连接服务器应用失败，TCP 建连被拒绝",
    ],
    "model_files_missing": [
        "模型目录找不到 config.json，加载立即失败",
        "指定本地权重路径不存在，提示 No such file or directory",
        "模型文件被移走，加载器无法读取 safetensors 文件",
        "本地模型路径为空，找不到 tokenizer 配置文件",
        "基础模型目录缺少配置文件，离线加载无法完成",
    ],
}
FAMILIES = {
    "train": [
        ("brief", "故障摘要：{signal}。"),
        ("operator", "值班同学报告：{signal}，请分类并给出下一项检查。"),
        ("log", "记录中出现：{signal}。请输出工单处理标签。"),
        ("user_report", "用户说：{signal}。现在先检查哪一项？"),
        ("single_issue", "本工单只有一个主要问题：{signal}。"),
        ("support", "技术支持收到请求：{signal}。请给出结构化判断。"),
        ("triage", "需要分诊的异常是：{signal}。"),
        ("incident", "实验异常：{signal}。请填写类别与检查动作。"),
        ("task", "处理下面的故障描述：{signal}。"),
        ("note", "排障便签：{signal}；先不要执行修复，只给检查建议。"),
    ],
    "validation": [
        ("handoff", "交接时发现一条未处理记录——{signal}。应分到哪类？"),
        ("dialogue", "甲问系统怎么了，乙答：{signal}。请生成处理条目。"),
        ("summary", "把这段现场情况整理为机器可读结果：{signal}。"),
        ("review", "复盘人员只确认以下现象：{signal}。选择下一项核查。"),
    ],
    "test": [
        ("ticket_form", "[待办工单]\n现场描述：{signal}\n请填写标准分类结果。"),
        (
            "chronology",
            "实验开始后系统没能继续。排查至今得到的明确证据是：{signal}。下一步如何分诊？",
        ),
        ("quote", "请根据引号内的现象选择类别及检查项：『{signal}』。"),
        ("machine_notice", "监测系统生成告警，正文如下：{signal}。请转成约定格式。"),
        ("helpdesk", "服务台要给该请求派发初步检查：{signal}。只处理这个已知现象。"),
    ],
}


def build():
    output = ROOT / "data"
    output.mkdir(parents=True, exist_ok=True)
    all_rows = {}
    for split, families in FAMILIES.items():
        rows = []
        for category, action in LABELS.items():
            for family_index, (family, template) in enumerate(families):
                repetitions = 2 if split == "train" else 1
                for variant in range(repetitions):
                    signal = SIGNALS[category][
                        (family_index + variant) % len(SIGNALS[category])
                    ]
                    rows.append(
                        {
                            "id": f"{split}-{category}-{family}-{variant}",
                            "split": split,
                            "template_family": family,
                            "prompt": template.format(signal=signal),
                            "target": {"category": category, "next_check": action},
                            "provenance": "synthetic_teaching_case",
                        }
                    )
        all_rows[split] = rows
        (output / f"{split}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
    manifest = {
        "dataset_id": "synthetic-ticket-classification-v1",
        "labels": LABELS,
        "counts": {split: len(rows) for split, rows in all_rows.items()},
        "families": {
            split: [family for family, _ in families]
            for split, families in FAMILIES.items()
        },
        "limitations": [
            "完全虚构的教学工单，不是实际实验室事故或生产数据。",
            "模板家庭不跨划分，但底层故障信号与标签映射共享，因此不代表未知故障或业务泛化。",
            "最终测试题在模型前后比较中保持相同；本轮不能根据该测试结果反复调参后继续称为未见测试。",
            "next_check 是本教学任务的固定动作标识，不意味着已实际执行检查。",
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
