#!/usr/bin/env bash
# MuseTalk avatar service entrypoint.
#
# 1. If the checkpoints volume is empty (first boot ever on this host),
#    run MuseTalk's download_weights.sh to populate it. ~3 GB of pulls from
#    HuggingFace, Google Drive, and pytorch.org.
# 2. Symlink the populated checkpoints dir into the MuseTalk repo so inference
#    finds `./models/*` relative to cwd.
# 3. Launch uvicorn.

set -euo pipefail

REPO_DIR="${MUSETALK_REPO_DIR:-/app/MuseTalk}"
VOLUME_DIR="/app/checkpoints"
PORT="${PORT:-8000}"

# The repo ships with `models/` NOT present; download_weights.sh creates it
# at `./models/*` inside cwd. We make that dir a symlink to the named volume
# so weights persist across container recreates.
if [ ! -L "${REPO_DIR}/models" ]; then
    rm -rf "${REPO_DIR}/models"
    mkdir -p "${VOLUME_DIR}"
    ln -s "${VOLUME_DIR}" "${REPO_DIR}/models"
fi

MARKER="${VOLUME_DIR}/musetalkV15/unet.pth"
if [ ! -s "${MARKER}" ]; then
    echo "[entrypoint] Weights missing — running MuseTalk's download_weights.sh"
    cd "${REPO_DIR}"
    # Patch: the script uses hf-mirror.com by default (for China). Swap to
    # the canonical HF endpoint so downloads succeed from most regions.
    sed -i 's|hf-mirror.com|huggingface.co|g' download_weights.sh
    bash download_weights.sh
else
    echo "[entrypoint] Weights already present at ${MARKER}"
fi

echo "[entrypoint] Starting avatar API on :${PORT}"
exec python -m uvicorn app:app --host 0.0.0.0 --port "${PORT}" --app-dir /app
