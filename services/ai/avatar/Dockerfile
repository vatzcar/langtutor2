# MuseTalk v1.5 avatar service.
#
# Audio-driven talking-head: source image/video + WAV -> MP4 with lip-sync.
# Swapped from LivePortrait because LivePortrait alone is video-driven and
# doesn't sync lips to audio. See services/ai/avatar/README.md.
#
# Build:   docker compose -f docker-compose.ai.yml build avatar
# VRAM:    ~3.5 GB at inference (v1.5, fp16 path).

FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl ffmpeg \
      libgl1 libglib2.0-0 libsndfile1 \
      python3.10 python3.10-dev python3-pip \
      build-essential pkg-config cmake \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/python3.10 /usr/bin/python3

WORKDIR /app

# Pin MuseTalk to a known-good ref. Override via build-arg when bumping.
ARG MUSETALK_REF=main
RUN git clone --depth 1 --branch ${MUSETALK_REF} \
    https://github.com/TMElyralab/MuseTalk.git /app/MuseTalk

# Install torch first with CUDA 12.1 wheels so MuseTalk's requirements.txt
# doesn't pull a CPU-only build.
RUN pip install --upgrade pip setuptools wheel && \
    pip install \
      torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 \
      --index-url https://download.pytorch.org/whl/cu121

# MuseTalk deps. Their requirements.txt pins some old versions; install as-is
# and patch any incompat at runtime if needed.
RUN pip install -r /app/MuseTalk/requirements.txt

# NOTE: mmlab stack (mmcv/mmdet/mmpose) is NOT installed here.
# MuseTalk's own requirements.txt doesn't list them, and their DWPose path
# loads a raw torch checkpoint (dw-ll_ucoco_384.pth) rather than going
# through mmpose. If a runtime ImportError for mmcv appears, add back:
#   RUN pip install --no-build-isolation mmengine \
#     && pip install --no-build-isolation mmcv==2.1.0 \
#        -f https://download.openmmlab.com/mmcv/dist/cu121/torch2.3/index.html

# FastAPI shim deps.
COPY requirements.txt /app/shim-requirements.txt
RUN pip install -r /app/shim-requirements.txt

# Shim code.
COPY app.py /app/app.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app/MuseTalk:/app
ENV MUSETALK_REPO_DIR=/app/MuseTalk
ENV MUSETALK_MODELS_DIR=/app/MuseTalk/models
ENV MUSETALK_VERSION=v15

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
