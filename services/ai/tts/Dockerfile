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
        git curl ca-certificates ffmpeg libsox-dev sox \
        build-essential pkg-config cmake \
        libsndfile1 \
        portaudio19-dev libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

# Many modern ML Python packages (tokenizers, pydantic-core) build via maturin
# and need a Rust toolchain at install time.
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- --default-toolchain stable --profile minimal -y \
    && echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> /etc/profile.d/cargo.sh
ENV PATH="/root/.cargo/bin:${PATH}"

RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/python3.10 /usr/bin/python3

WORKDIR /app

# Shallow-clone fish-speech at a known-good ref. Override FISH_REF at build
# time to move forward when upstream lands changes.
ARG FISH_REF=v1.5.0
RUN git clone --depth 1 --branch ${FISH_REF} \
    https://github.com/fishaudio/fish-speech.git /app/fish-speech

WORKDIR /app/fish-speech

# Split the pip installs into separate RUN layers so build failures show
# which step actually broke. Torch wheels come from the pytorch index so we
# don't accidentally pull the CPU-only build.
RUN pip install --upgrade pip setuptools wheel

RUN pip install \
      torch==2.3.1 \
      torchaudio==2.3.1 \
      --index-url https://download.pytorch.org/whl/cu121

RUN pip install -e .

RUN pip install \
      "fastapi>=0.110" \
      "uvicorn[standard]>=0.29" \
      "pyrootutils" \
      "loguru" \
      "huggingface_hub>=0.23"

# Pre-make the checkpoint dir so the mounted volume has the right ownership.
RUN mkdir -p /app/checkpoints

EXPOSE 8080

# Entrypoint wrapper: pulls weights on first run, then starts the API server.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
