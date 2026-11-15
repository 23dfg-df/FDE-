#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HAYSTACK_TELEMETRY_ENABLED=false
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
exec .venv-app/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port "${CAPSTONE_PORT:-18300}" --workers 1
