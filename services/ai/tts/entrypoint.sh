#!/usr/bin/env bash
# Fish-Speech S2 TTS entrypoint.
# Downloads model weights on first run, then starts the HTTP API server.

set -euo pipefail

CKPT_DIR="${FISH_SPEECH_CHECKPOINT_DIR:-/app/checkpoints}"
CKPT_NAME="${FISH_SPEECH_CHECKPOINT:-fish-speech-1.5}"
MODEL_PATH="${CKPT_DIR}/${CKPT_NAME}"
PORT="${PORT:-8080}"

mkdir -p "${CKPT_DIR}"

if [ ! -d "${MODEL_PATH}" ] || [ -z "$(ls -A "${MODEL_PATH}" 2>/dev/null)" ]; then
    echo "[entrypoint] Downloading Fish-Speech weights: ${CKPT_NAME}"
    python -c "
from huggingface_hub import snapshot_download
import os
snapshot_download(
    repo_id='fishaudio/${CKPT_NAME}',
    local_dir='${MODEL_PATH}',
    local_dir_use_symlinks=False,
)
"
else
    echo "[entrypoint] Weights already present at ${MODEL_PATH}"
fi

cd /app/fish-speech

# Fish-Speech provides an HTTP API server module. Serve on all interfaces so
# Docker port-mapping works.
echo "[entrypoint] Starting Fish-Speech API server on :${PORT}"
exec python -m tools.api_server \
    --listen "0.0.0.0:${PORT}" \
    --llama-checkpoint-path "${MODEL_PATH}" \
    --decoder-checkpoint-path "${MODEL_PATH}/firefly-gan-vq-fsq-8x1024-21hz-generator.pth" \
    --decoder-config-name firefly_gan_vq \
    --compile
