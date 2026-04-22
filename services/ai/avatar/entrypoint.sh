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
    echo "[entrypoint] Weights missing — patching and running MuseTalk's download_weights.sh"
    cd "${REPO_DIR}"

    # Patch 1: hf-mirror.com (China default) -> canonical HF endpoint.
    sed -i 's|hf-mirror.com|huggingface.co|g' download_weights.sh

    # Patch 2: the script runs `pip install -U "huggingface_hub[cli]"` which
    # bumps HF hub to 1.x, which (a) removes the `huggingface-cli` entry
    # point that the rest of the script uses (replaced by `hf`) and (b)
    # breaks MuseTalk's pinned tokenizers/transformers. Neuter the upgrade:
    # hf-hub 0.30.2 (already installed by MuseTalk's requirements.txt) still
    # provides `huggingface-cli download` and works with tokenizers 0.15.2.
    sed -i 's|pip install -U "huggingface_hub\[cli\]"|echo "skip hf-hub upgrade"|' download_weights.sh

    # Patch 3: current gdown no longer accepts --id. The value passes
    # positionally. Strip ' --id '.
    sed -i 's| --id | |g' download_weights.sh

    # Patch 4: make the script abort on the first real failure instead of
    # lying with "All weights downloaded successfully" after a partial run.
    sed -i '2i set -euo pipefail' download_weights.sh

    bash download_weights.sh
else
    echo "[entrypoint] Weights already present at ${MARKER}"
fi

echo "[entrypoint] Starting avatar API on :${PORT}"
exec python -m uvicorn app:app --host 0.0.0.0 --port "${PORT}" --app-dir /app
