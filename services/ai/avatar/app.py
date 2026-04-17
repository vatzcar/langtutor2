"""FastAPI shim around KwaiVGI/LivePortrait.

This is a *best-effort* wrapper — LivePortrait ships as a CLI / Python
module, not a web service. The exact call signature varies between
upstream commits. On first deployment you will likely need to:

  1. Open /app/LivePortrait and inspect `inference.py` or the README
     for the current pipeline entrypoint (e.g. ``LivePortraitPipeline``
     or ``inference.main``).
  2. Adjust ``_load_pipeline`` and ``_render`` below to match.
  3. Download the pretrained weights. See the upstream README — typically
     `python inference.py` on first run will pull weights into
     ``pretrained_weights/``. Pre-download into the mounted volume to
     keep weights across container rebuilds.

The service exposes:
  GET  /health                -> {"status": "ok"}
  POST /render  (multipart)   -> MP4 bytes
      fields: audio (wav), portrait (jpg/png)
  WS   /stream                -> real-time streaming (stub; see below)
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger("avatar")
logging.basicConfig(level=logging.INFO)

CHECKPOINT_DIR = os.environ.get("LIVEPORTRAIT_CHECKPOINT_DIR", "/app/checkpoints")
DEVICE = os.environ.get("LIVEPORTRAIT_DEVICE", "cuda")

app = FastAPI(title="LangTutor Avatar (LivePortrait)")

_pipeline = None  # Lazy-loaded singleton.


def _load_pipeline():
    """Load the LivePortrait pipeline once.

    The upstream API has shifted across commits. We try a couple of
    common import paths and fall back to a placeholder that echoes
    the input so the rest of the stack can be wired up.
    """
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    try:
        # Path as of mid-2024; may change upstream.
        from src.live_portrait_pipeline import LivePortraitPipeline  # type: ignore
        from src.config.argument_config import ArgumentConfig  # type: ignore
        from src.config.crop_config import CropConfig  # type: ignore
        from src.config.inference_config import InferenceConfig  # type: ignore

        inference_cfg = InferenceConfig()
        crop_cfg = CropConfig()
        args = ArgumentConfig()
        _pipeline = LivePortraitPipeline(
            inference_cfg=inference_cfg, crop_cfg=crop_cfg
        )
        logger.info("LivePortrait pipeline loaded via src.live_portrait_pipeline.")
        return _pipeline
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not load LivePortrait pipeline from expected module (%s). "
            "Falling back to stub — adjust services/ai/avatar/app.py to match "
            "your upstream version.",
            exc,
        )
        _pipeline = _StubPipeline()
        return _pipeline


class _StubPipeline:
    """Fallback used when the real pipeline can't be imported.

    Returns a 1x1 black MP4 so callers can still exercise the API surface.
    """

    def execute(self, audio_path: str, portrait_path: str, output_path: str) -> str:
        import subprocess

        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return output_path


@app.on_event("startup")
async def _startup() -> None:
    Path(CHECKPOINT_DIR).mkdir(parents=True, exist_ok=True)
    # Load the pipeline eagerly so the first request isn't 30s slow.
    await asyncio.get_event_loop().run_in_executor(None, _load_pipeline)


@app.get("/health")
async def health() -> JSONResponse:
    ready = _pipeline is not None
    return JSONResponse({"status": "ok" if ready else "loading", "device": DEVICE})


@app.post("/render")
async def render(
    audio: UploadFile = File(...),
    portrait: UploadFile = File(...),
) -> Response:
    """Synchronous render: audio + portrait -> MP4 bytes."""
    pipeline = _load_pipeline()

    with tempfile.TemporaryDirectory() as td:
        audio_path = os.path.join(td, "audio.wav")
        portrait_path = os.path.join(td, "portrait" + Path(portrait.filename or "p.jpg").suffix)
        output_path = os.path.join(td, "out.mp4")

        with open(audio_path, "wb") as f:
            f.write(await audio.read())
        with open(portrait_path, "wb") as f:
            f.write(await portrait.read())

        def _run() -> str:
            if hasattr(pipeline, "execute"):
                return pipeline.execute(audio_path, portrait_path, output_path)
            # Newer upstream API variants:
            if hasattr(pipeline, "__call__"):
                return pipeline(audio=audio_path, source=portrait_path, output=output_path)  # type: ignore
            raise RuntimeError("Pipeline has no recognized entrypoint.")

        try:
            await asyncio.get_event_loop().run_in_executor(None, _run)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Render failed.")
            return JSONResponse({"error": str(exc)}, status_code=500)

        with open(output_path, "rb") as f:
            video_bytes = f.read()

    return Response(content=video_bytes, media_type="video/mp4")


@app.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    """Real-time streaming endpoint (stub).

    Protocol (proposed, subject to change once upstream streaming API is chosen):
      client -> server: binary PCM16 audio frames (20ms @ 16kHz)
      server -> client: binary H.264-in-MP4 chunks or raw frames

    Upstream LivePortrait does not yet have a canonical streaming
    interface. Implement by chunking audio into windows and invoking
    the pipeline repeatedly, or port the TensorRT real-time branch.
    """
    await ws.accept()
    try:
        while True:
            data = await ws.receive_bytes()
            # TODO: feed `data` into a streaming inference loop and yield frames.
            await ws.send_bytes(b"")  # placeholder ack
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stream error: %s", exc)
        await ws.close(code=1011)
