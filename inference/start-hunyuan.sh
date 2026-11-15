#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CUDA_VISIBLE_DEVICES="${FDE_PHYSICAL_GPU:-0}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MAX_JOBS=2
export TORCHINDUCTOR_COMPILE_THREADS=2 VLLM_NO_USAGE_STATS=1
export VLLM_HOST_IP=127.0.0.1 DO_NOT_TRACK=1
model_path="${FDE_MODEL_PATH:-$PWD/../models/Hunyuan-1.8B-Instruct}"
if [[ ! -f "$model_path/model.safetensors" ]]; then
  echo "缺少混元权重，请先运行 inference/download-hunyuan.py。" >&2
  exit 1
fi
if [[ ! "$CUDA_VISIBLE_DEVICES" =~ ^[0-9]+$ ]]; then
  echo "FDE_PHYSICAL_GPU 必须为单张物理GPU编号。" >&2
  exit 1
fi
free_mib=$(nvidia-smi --id="$CUDA_VISIBLE_DEVICES" --query-gpu=memory.free --format=csv,noheader,nounits)
if (( free_mib < 12288 )); then
  echo "目标卡当前可用显存不足12 GiB，请等待资源空闲。" >&2
  exit 1
fi
# 默认0.28针对32GiB卡，属于实例显存规划，不是算力限额或系统级隔离。
exec "${FDE_VLLM_BIN:-$PWD/.venv-vllm/bin/vllm}" serve "$model_path" \
  --served-model-name tencent/Hunyuan-1.8B-Instruct \
  --host 127.0.0.1 --port 18301 --dtype bfloat16 \
  --gpu-memory-utilization "${FDE_GPU_MEMORY_UTILIZATION:-0.28}" \
  --max-model-len 2048 --max-num-seqs 1 --max-num-batched-tokens 2048 \
  --enforce-eager --generation-config auto --no-enable-prefix-caching --seed 42
