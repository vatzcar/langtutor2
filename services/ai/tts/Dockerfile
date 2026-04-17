# Fish-Speech S2 TTS service built from source.
#
# Fish-Audio does not publish an official Docker image, so we build from their
# GitHub repo. The container exposes an HTTP API on :8080 via the `tools.api_server`
# module documented in their README.
#
# Build:  docker compose -f docker-compose.ai.yml build tts
# First-run downloads weights (~2GB) into /app/checkpoints (bind-mounted volume).

ARG PYTHON_VERSION=3.10
ARG CUDA_VERSION=12.1.1
ARG UBUNTU_VERSION=22.04

FROM nvidia/cuda:${CUDA_VERSION}-cudnn8-runtime-ubuntu${UBUNTU_VERSION}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/checkpoints \
    HUGGINGFACE_HUB_CACHE=/app/checkpoints

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3-pip python3.10-dev python3.10-venv \
        git curl ffmpeg libsox-dev sox \
        build-essential pkg-config \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/python3.10 /usr/bin/python3

WORKDIR /app

# Shallow-clone fish-speech at a known-good ref. Override FISH_REF at build
# time to move forward when upstream lands changes.
ARG FISH_REF=main
RUN git clone --depth 1 --branch ${FISH_REF} \
    https://github.com/fishaudio/fish-speech.git /app/fish-speech

WORKDIR /app/fish-speech

# Fish-Speech declares its deps in pyproject.toml.
# We install torch with CUDA 12.1 wheels explicitly so pip doesn't fetch the
# CPU-only wheel by accident.
RUN pip install --upgrade pip setuptools wheel && \
    pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121 && \
    pip install -e . && \
    pip install "fastapi>=0.110" "uvicorn[standard]>=0.29" "pyrootutils" "loguru"

# Pre-make the checkpoint dir so the mounted volume has the right ownership.
RUN mkdir -p /app/checkpoints

EXPOSE 8080

# Entrypoint wrapper: pulls weights on first run, then starts the API server.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
