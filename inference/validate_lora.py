"""只读、CPU 适配器预检；完成标记与权重哈希不通过则禁止切换服务。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

BASE_PATH = Path("/home/learner/test/inference-demo/model")


def validate_metadata(adapter: Path, base: Path = BASE_PATH) -> dict[str, Any]:
    summary = json.loads((adapter.parent / "summary.json").read_text())
    config = json.loads((adapter / "adapter_config.json").read_text())
    if summary.get("status") != "completed":
        raise ValueError("训练及独立重载尚未完成")
    if not summary.get("reload_all_answers_match"):
        raise ValueError("训练后的独立重载回答不一致，需先复核")
    if config.get("peft_type") != "LORA" or config.get("task_type") != "CAUSAL_LM":
        raise ValueError("适配器不是本实验需要的 CAUSAL_LM LoRA")
    if config.get("r") != 8:
        raise ValueError("本次部署仅接受 rank 8")
    if set(config.get("target_modules", [])) != {"q_proj", "v_proj"}:
        raise ValueError("target_modules 与本次训练约定不一致")
    if config.get("modules_to_save") or config.get("use_dora"):
        raise ValueError("vLLM 0.11.2 不支持本次额外保存模块或 DoRA")
    if config.get("bias", "none") != "none":
        raise ValueError("此部署要求 bias=none")
    if Path(config["base_model_name_or_path"]).resolve() != base.resolve():
        raise ValueError("适配器基础模型路径不一致")
    hashes = {}
    for name in ("adapter_config.json", "adapter_model.safetensors"):
        digest = hashlib.sha256((adapter / name).read_bytes()).hexdigest()
        if summary.get("adapter_sha256", {}).get(name) != digest:
            raise ValueError(f"{name} 与训练完成报告的哈希不一致")
        hashes[name] = digest
    return {
        "status": "compatible_metadata",
        "adapter_path": str(adapter.resolve()),
        "base_model_path": str(base.resolve()),
        "config": config,
        "sha256": hashes,
        "training_status": summary["status"],
        "independent_reload_answers_match": True,
    }


def validate_runtime(adapter: Path) -> dict[str, Any]:
    # 只在服务器独立环境调用；本地契约测试不依赖 torch/vllm。
    import torch
    from safetensors import safe_open
    from vllm.config.lora import LoRAConfig
    from vllm.lora.peft_helper import PEFTHelper

    torch.set_num_threads(2)
    helper = PEFTHelper.from_local_dir(str(adapter), max_position_embeddings=2048)
    helper.validate_legal(LoRAConfig(max_lora_rank=8, max_loras=1))
    count = 0
    parameters = 0
    with safe_open(
        adapter / "adapter_model.safetensors", framework="pt", device="cpu"
    ) as tensors:
        for name in tensors.keys():
            if "lora_A" not in name and "lora_B" not in name:
                raise ValueError(f"意外的非 LoRA 张量: {name}")
            value = tensors.get_tensor(name)
            if value.ndim != 2 or 8 not in value.shape:
                raise ValueError(f"LoRA 张量形状与 rank 不符: {name}")
            if not torch.isfinite(value).all().item():
                raise ValueError(f"LoRA 张量包含非有限值: {name}")
            count += 1
            parameters += value.numel()
    if not count:
        raise ValueError("适配器没有权重张量")
    return {
        "vllm_peft_helper": "passed",
        "tensor_count": count,
        "parameters": parameters,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("adapter", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate_metadata(args.adapter)
    result["runtime_validation"] = validate_runtime(args.adapter)
    result["status"] = "compatible"
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
