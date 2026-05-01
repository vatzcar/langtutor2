#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${LIVEPORTRAIT_REPO_DIR:-/app/LivePortrait}"
MODELS_DIR="${LIVEPORTRAIT_MODELS_DIR:-/app/LivePortrait/pretrained_weights}"
VOLUME_DIR="${LIVEPORTRAIT_CHECKPOINT_DIR:-/app/checkpoints}"
PORT="${PORT:-8000}"

# ── Persist weights in the named volume ──────────────────────────
# The volume is mounted at $VOLUME_DIR. Symlink the repo's expected
# weights path to the volume so downloads survive rebuilds.
mkdir -p "${VOLUME_DIR}/liveportrait"
if [ ! -L "${MODELS_DIR}" ]; then
    rm -rf "${MODELS_DIR}"
    ln -s "${VOLUME_DIR}/liveportrait" "${MODELS_DIR}"
fi

# ── Download weights on first run ────────────────────────────────
MARKER="${VOLUME_DIR}/liveportrait/liveportrait/base_models/appearance_feature_extractor.pth"

if [ ! -s "${MARKER}" ]; then
    echo "[entrypoint] Downloading LivePortrait pretrained weights..."
    set -x
    python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='KwaiVGI/LivePortrait',
    local_dir='${VOLUME_DIR}/liveportrait',
    local_dir_use_symlinks=False,
)
"
    set +x
    echo "[entrypoint] Weight download complete."
else
    echo "[entrypoint] LivePortrait weights already present."
fi

# ── Download driving video if not present ────────────────────────
DRIVING_DIR="${VOLUME_DIR}/liveportrait/idle_driving"
DRIVING_VIDEO="${DRIVING_DIR}/idle_motion_reference.mp4"

if [ ! -s "${DRIVING_VIDEO}" ]; then
    echo "[entrypoint] Downloading idle-motion driving video..."
    mkdir -p "${DRIVING_DIR}"
    # Pexels stock video — woman with neutral idle expression, CC0.
    # Replace this URL with a self-hosted or properly licensed clip.
    curl -fSL -o "${DRIVING_VIDEO}" \
        "https://videos.pexels.com/video-files/5529530/5529530-hd_1080_1920_25fps.mp4" \
        || echo "[entrypoint] WARNING: driving video download failed. /render will error until a driving video is placed at ${DRIVING_VIDEO}"
else
    echo "[entrypoint] Driving video already present."
fi

echo "[entrypoint] Starting LivePortrait API on port ${PORT}..."
exec python -m uvicorn app:app --host 0.0.0.0 --port "${PORT}" --app-dir /app
