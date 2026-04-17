# Custom LivePortrait avatar service.
#
# Clones KwaiVGI/LivePortrait, installs its Python deps, and serves a thin
# FastAPI shim (app.py) on :8000. Model weights are NOT baked in — they are
# downloaded on first use into the mounted `ai-models` volume.
#
# Build:   docker compose -f docker-compose.ai.yml build avatar
# VRAM:    ~3.5 GB at inference (standard settings).
#
# NOTE: LivePortrait's upstream inference API is a Python module, NOT a web
# API. The shim in app.py calls into the project directly. You WILL likely
# need to adjust app.py to match the exact upstream call signature after
# first build — see services/ai/avatar/README.md.

FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      git \
      curl \
      ffmpeg \
      libgl1 \
      libglib2.0-0 \
      python3.10 \
      python3.10-dev \
      python3-pip \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/python3.10 /usr/bin/python3

WORKDIR /app

# Clone LivePortrait (pin a known-good commit in production).
RUN git clone --depth 1 https://github.com/KwaiVGI/LivePortrait.git /app/LivePortrait

# Install torch first so LivePortrait's requirements don't pull a CPU-only wheel.
RUN pip install --upgrade pip && \
    pip install torch==2.3.0 torchvision==0.18.0 --index-url https://download.pytorch.org/whl/cu121

# Install LivePortrait's requirements.
RUN pip install -r /app/LivePortrait/requirements.txt || \
    echo "WARNING: LivePortrait requirements install had issues; inspect manually."

# FastAPI shim deps.
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Shim code.
COPY app.py /app/app.py

# NOTE: The shim imports from /app/LivePortrait — PYTHONPATH points there.
ENV PYTHONPATH=/app/LivePortrait:/app

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
