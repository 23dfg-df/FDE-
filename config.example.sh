#!/usr/bin/env bash
# 在项目根目录 source config.example.sh；可在调用前设置变量覆盖默认值。
export FDE_MODEL_PATH="${FDE_MODEL_PATH:-$PWD/../models/Hunyuan-1.8B-Instruct}"
export FDE_PHYSICAL_GPU="${FDE_PHYSICAL_GPU:-0}"
export FDE_GPU_MEMORY_UTILIZATION="${FDE_GPU_MEMORY_UTILIZATION:-0.28}"
export CAPSTONE_TOKENIZER="$FDE_MODEL_PATH"
export CAPSTONE_EMBEDDING="${CAPSTONE_EMBEDDING:-$PWD/../models/bge-small-zh-v1.5}"
export CAPSTONE_RERANKER="${CAPSTONE_RERANKER:-$PWD/../models/bge-reranker-base}"
export CAPSTONE_MODEL_URL="${CAPSTONE_MODEL_URL:-http://127.0.0.1:18301/v1}"
export CAPSTONE_MODEL_NAME="tencent/Hunyuan-1.8B-Instruct"
