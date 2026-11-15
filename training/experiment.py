"""隔离进程运行 QLoRA 工单分类、保存适配器、完整重载评测。"""

import argparse
import hashlib
import json
import os
import random
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from common import SYSTEM, atomic_json, load_data, score_answer, summarize

HERE = Path(__file__).resolve().parent


def encode_dataset(tokenizer, groups, limit):
    encoded = {}
    maximum = 0
    for split, rows in groups.items():
        encoded[split] = []
        for row in rows:
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": row["prompt"]},
            ]
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True
            )
            answer = json.dumps(
                row["target"], ensure_ascii=False, separators=(",", ":")
            )
            full = tokenizer.apply_chat_template(
                messages + [{"role": "assistant", "content": answer}],
                tokenize=True,
                add_generation_prompt=False,
            )
            if full[: len(prompt)] != prompt:
                raise ValueError("聊天模板的回答前缀不一致，不能正确构造监督标签")
            if len(full) > limit or len(full) <= len(prompt):
                raise ValueError(
                    f"{row['id']} 的完整标签长度 {len(full)} "
                    f"超出限制 {limit}，不允许截断"
                )
            maximum = max(maximum, len(full))
            encoded[split].append(
                {
                    "input_ids": full,
                    "labels": [-100] * len(prompt) + full[len(prompt) :],
                    "prompt_ids": prompt,
                }
            )
    return encoded, maximum


def check_data(model_path, data_dir, limit):
    from transformers import AutoTokenizer

    groups, audit = load_data(data_dir)
    tokenizer = AutoTokenizer.from_pretrained(
        model_path, local_files_only=True, trust_remote_code=False
    )
    encoded, maximum = encode_dataset(tokenizer, groups, limit)
    del encoded
    return {
        **audit,
        "maximum_full_sequence_tokens": maximum,
        "sequence_limit": limit,
        "all_labels_fit_without_truncation": True,
    }


def worker(config, output, stage):
    import bitsandbytes
    import peft
    import torch
    import transformers
    from peft import (
        LoraConfig,
        PeftModel,
        get_peft_model,
        prepare_model_for_kbit_training,
    )
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    began = time.perf_counter()
    torch.set_num_threads(2)
    torch.manual_seed(config["seed"])
    random.seed(config["seed"])
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("需要通过 CUDA_VISIBLE_DEVICES 仅暴露目标 GPU，不自动切换")
    device = torch.device("cuda:0")
    torch.cuda.set_device(device)
    free, total = torch.cuda.mem_get_info(device)
    if free < 10 * 1024**3:
        raise RuntimeError(f"需要至少 10 GiB 空闲显存；当前 {free / 1024**3:.2f} GiB")
    torch.cuda.reset_peak_memory_stats(device)
    groups, audit = load_data(config["data_dir"])
    tokenizer = AutoTokenizer.from_pretrained(
        config["model_path"], local_files_only=True, trust_remote_code=False
    )
    tokenizer.pad_token = tokenizer.eos_token
    encoded, maximum = encode_dataset(tokenizer, groups, config["max_length"])
    base = AutoModelForCausalLM.from_pretrained(
        config["model_path"],
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        dtype=torch.bfloat16,
        device_map={"": 0},
        attn_implementation="sdpa",
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        ),
    )
    base = prepare_model_for_kbit_training(
        base,
        use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    base.config.use_cache = False
    if stage == "train":
        model = get_peft_model(
            base,
            LoraConfig(
                r=config["rank"],
                lora_alpha=config["rank"] * 2,
                lora_dropout=0.0,
                target_modules=["q_proj", "v_proj"],
                bias="none",
                task_type="CAUSAL_LM",
            ),
        )
    else:
        model = PeftModel.from_pretrained(
            base, output / "adapter", is_trainable=False, local_files_only=True
        )
    state = {
        "stage": stage,
        "status": "running",
        "optimizer_step": 0,
        "detail": "模型已加载",
        "curves": [],
    }

    def progress(detail, **values):
        state.update(detail=detail, **values)
        atomic_json(output / "progress.json", state)

    def loss_for(item, train=False):
        ids = torch.tensor([item["input_ids"]], device=device)
        labels = torch.tensor([item["labels"]], device=device)
        return model(
            input_ids=ids,
            attention_mask=torch.ones_like(ids),
            labels=labels,
            use_cache=False,
        ).loss

    def validation_loss():
        model.eval()
        summed, count = 0.0, 0
        with torch.inference_mode():
            for item in encoded["validation"]:
                active_tokens = sum(label != -100 for label in item["labels"][1:])
                summed += float(loss_for(item).float().cpu()) * active_tokens
                count += active_tokens
        return summed / count

    def evaluate(label):
        model.eval()
        results = []
        for index, (row, item) in enumerate(zip(groups["test"], encoded["test"])):
            progress(f"{label}：评测 {index + 1}/{len(groups['test'])}")
            ids = torch.tensor([item["prompt_ids"]], device=device)
            torch.cuda.synchronize(device)
            started = time.perf_counter()
            with torch.inference_mode():
                generated = model.generate(
                    input_ids=ids,
                    attention_mask=torch.ones_like(ids),
                    max_new_tokens=64,
                    do_sample=False,
                    use_cache=True,
                    pad_token_id=tokenizer.eos_token_id,
                )
            torch.cuda.synchronize(device)
            answer_ids = generated[0, ids.shape[1] :]
            answer = tokenizer.decode(answer_ids, skip_special_tokens=True)
            results.append(
                {
                    "id": row["id"],
                    "prompt": row["prompt"],
                    "target": row["target"],
                    "answer": answer,
                    "checks": score_answer(answer, row["target"]),
                    "input_tokens": ids.shape[1],
                    "output_tokens": len(answer_ids),
                    "elapsed_seconds": time.perf_counter() - started,
                }
            )
        return {"label": label, "items": results, "summary": summarize(results)}

    environment = {
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "peft": peft.__version__,
        "bitsandbytes": bitsandbytes.__version__,
        "cuda_runtime": torch.version.cuda,
        "gpu_name": torch.cuda.get_device_name(device),
        "physical_gpu": config["physical_gpu"],
        "logical_device": "cuda:0",
        "initial_free_mib": free / 1024**2,
        "total_mib": total / 1024**2,
    }
    if stage == "train":
        # 在统一 k-bit 准备和零增量 LoRA 初始化之后测基线，避免精度差异污染对照。
        progress("运行零增量适配器基线")
        before = evaluate("before")
        before_loss = validation_loss()
        atomic_json(output / "before.json", {**before, "validation_loss": before_loss})
        trainable = [
            parameter for parameter in model.parameters() if parameter.requires_grad
        ]
        optimizer = torch.optim.AdamW(trainable, lr=config["learning_rate"])
        ordering = list(range(len(encoded["train"])))
        rng = random.Random(config["seed"])
        rng.shuffle(ordering)
        cursor = 0
        state["curves"] = [
            {"step": 0, "train_loss": None, "validation_loss": before_loss}
        ]
        for step in range(1, config["steps"] + 1):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            total_loss = 0.0
            for _ in range(config["gradient_accumulation"]):
                if cursor == len(ordering):
                    rng.shuffle(ordering)
                    cursor = 0
                sample = encoded["train"][ordering[cursor]]
                cursor += 1
                loss = loss_for(sample, train=True)
                if not torch.isfinite(loss):
                    raise RuntimeError("训练损失不是有限值")
                total_loss += float(loss.detach().float().cpu())
                (loss / config["gradient_accumulation"]).backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            optimizer.step()
            point = {
                "step": step,
                "train_loss": total_loss / config["gradient_accumulation"],
                "validation_loss": validation_loss()
                if step % 10 == 0 or step == config["steps"]
                else None,
            }
            state["curves"].append(point)
            progress(f"完成参数更新 {step}/{config['steps']}", optimizer_step=step)
        after = evaluate("after")
        after_loss = validation_loss()
        model.save_pretrained(output / "adapter", safe_serialization=True)
        result = {
            "status": "completed",
            "environment": environment,
            "dataset_audit": audit,
            "maximum_full_sequence_tokens": maximum,
            "trainable_parameters": sum(parameter.numel() for parameter in trainable),
            "total_parameters_reported": sum(
                parameter.numel() for parameter in model.parameters()
            ),
            "before": before,
            "after": after,
            "validation_loss_before": before_loss,
            "validation_loss_after": after_loss,
            "curves": state["curves"],
            "peak_allocated_mib": torch.cuda.max_memory_allocated(device) / 1024**2,
            "wall_seconds": time.perf_counter() - began,
            "baseline_precision_note": (
                "NF4+BF16，经相同k-bit准备和零增量LoRA初始化；"
                "同一测试题与生成设置"
            ),
        }
        atomic_json(output / "training-result.json", result)
    else:
        reloaded = evaluate("reloaded")
        original = json.loads((output / "training-result.json").read_text("utf-8"))
        comparisons = [
            {"id": old["id"], "matches": old["answer"] == new["answer"]}
            for old, new in zip(original["after"]["items"], reloaded["items"])
        ]
        result = {
            "status": "completed",
            "environment": environment,
            "evaluation": reloaded,
            "validation_loss": validation_loss(),
            "comparisons": comparisons,
            "all_answers_match": all(item["matches"] for item in comparisons),
            "peak_allocated_mib": torch.cuda.max_memory_allocated(device) / 1024**2,
            "wall_seconds": time.perf_counter() - began,
            "process_isolation": (
                "training process exited before reload process started"
            ),
        }
        atomic_json(output / "reload-result.json", result)
    progress("本阶段完成", status="completed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path("/home/learner/test/inference-demo/model"),
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--physical-gpu", choices=["0", "1"], default="0")
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--check-data", action="store_true")
    parser.add_argument("--internal-stage", choices=["train", "reload"])
    args = parser.parse_args()
    if not 60 <= args.steps <= 100:
        parser.error("steps 需要在 60 到 100 之间")
    if args.check_data:
        print(
            json.dumps(
                check_data(args.model_path, HERE / "data", 256),
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if args.internal_stage:
        config = json.loads((args.output_dir / "config.json").read_text("utf-8"))
        worker(config, args.output_dir, args.internal_stage)
        return
    output = (
        args.output_dir
        or HERE.parent
        / "evidence/training"
        / datetime.now().strftime("run-%Y%m%d-%H%M%S")
    ).resolve()
    output.mkdir(parents=True, exist_ok=False)
    config = {
        "model_path": str(args.model_path.resolve()),
        "data_dir": str(HERE / "data"),
        "physical_gpu": args.physical_gpu,
        "steps": args.steps,
        "learning_rate": 0.0002,
        "rank": 8,
        "max_length": 256,
        "gradient_accumulation": 4,
        "batch_size": 1,
        "seed": 42,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(output / "config.json", config)
    child = None

    def stop_child(signum=None, frame=None):
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=10)
        if signum is not None:
            raise KeyboardInterrupt(f"收到信号 {signum}")

    signal.signal(signal.SIGTERM, stop_child)
    signal.signal(signal.SIGINT, stop_child)
    started = time.perf_counter()
    try:
        environment = {
            **os.environ,
            "CUDA_VISIBLE_DEVICES": args.physical_gpu,
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2",
            "TOKENIZERS_PARALLELISM": "false",
        }
        for stage in ("train", "reload"):
            with (output / f"{stage}.log").open("w", encoding="utf-8") as log:
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-u",
                        str(Path(__file__).resolve()),
                        "--internal-stage",
                        stage,
                        "--output-dir",
                        str(output),
                    ],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env=environment,
                    start_new_session=True,
                )
                code = child.wait(timeout=1800 if stage == "train" else 600)
            if code:
                raise RuntimeError(f"{stage} 子进程退出码 {code}，见 {stage}.log")
            print(
                json.dumps(
                    {
                        "stage": stage,
                        "subprocess_exited": True,
                        "output_dir": str(output),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        training = json.loads((output / "training-result.json").read_text("utf-8"))
        reload_result = json.loads((output / "reload-result.json").read_text("utf-8"))
        manifest = {
            "status": "completed",
            "config": config,
            "before": training["before"]["summary"],
            "after": training["after"]["summary"],
            "reloaded": reload_result["evaluation"]["summary"],
            "reload_all_answers_match": reload_result["all_answers_match"],
            "validation_loss_before": training["validation_loss_before"],
            "validation_loss_after": training["validation_loss_after"],
            "wall_seconds": time.perf_counter() - started,
            "adapter_sha256": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (output / "adapter").iterdir()
                if p.is_file()
            },
            "limitations": [
                "合成四分类教学任务，不能声称业务泛化或通用模型能力提高",
                "模板家庭分离，但底层故障信号共享",
                "规则分数仅衡量约定JSON字段与标签",
                "训练与重载均为独立子进程；张量显存峰值不等于整卡占用",
            ],
        }
        atomic_json(output / "summary.json", manifest)
        with ZipFile(output / "ticket-adapter.zip", "w", ZIP_DEFLATED) as bundle:
            for path in (output / "adapter").rglob("*"):
                if path.is_file():
                    bundle.write(
                        path, "adapter/" + str(path.relative_to(output / "adapter"))
                    )
            bundle.write(output / "summary.json", "summary.json")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    except BaseException as error:
        stop_child()
        atomic_json(
            output / "failure.json",
            {
                "status": "failed",
                "error": str(error),
                "wall_seconds": time.perf_counter() - started,
            },
        )
        raise


if __name__ == "__main__":
    main()
