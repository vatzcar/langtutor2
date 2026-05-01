# LivePortrait — portrait-to-idle-video service for LangTutor.
#
# Produces a looping idle-motion MP4 from a single portrait image +
# a shared driving video. Run once per persona; output is reused by
# the MuseTalk lip-sync service at session time.
#
# VRAM: ~4 GB peak during inference (fp16).

ARG CUDA_TAG=12.1.1-cudnn8-devel-ubuntu22.04
FROM nvidia/cuda:${CUDA_TAG}

ARG DEBIAN_FRONTEND=noninteractive
ARG LIVEPORTRAIT_REF=v0.5.0

# ── System deps ──────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ffmpeg \
        libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
        python3.10 python3.10-venv python3.10-dev python3-pip \
        build-essential pkg-config cmake \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps (torch first, then LivePortrait requirements) ────
RUN pip install --no-cache-dir \
        torch==2.3.1 torchvision==0.18.1 \
        --index-url https://download.pytorch.org/whl/cu121

RUN git clone --depth 1 --branch ${LIVEPORTRAIT_REF} \
        https://github.com/KwaiVGI/LivePortrait.git /app/LivePortrait

RUN pip install --no-cache-dir -r /app/LivePortrait/requirements.txt

# FastAPI shim deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# ── Environment ──────────────────────────────────────────────────
ENV PYTHONPATH=/app/LivePortrait:/app
ENV LIVEPORTRAIT_REPO_DIR=/app/LivePortrait
ENV LIVEPORTRAIT_MODELS_DIR=/app/LivePortrait/pretrained_weights
ENV LIVEPORTRAIT_DEVICE=cuda

# ── App code ─────────────────────────────────────────────────────
COPY app.py /app/app.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
