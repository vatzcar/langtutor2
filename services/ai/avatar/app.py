"""FastAPI shim around TMElyralab/MuseTalk (v1.5).

MuseTalk does audio-driven talking-head video: given a source video (or image)
of a person's face + a WAV of speech, it produces an MP4 with lip-sync'd face.

Endpoints:
    GET  /health
    POST /render (multipart) -> video/mp4
        audio:  WAV file (required)
        source: MP4 video or image (jpg/png) of the speaker's face (required)
        bbox_shift: optional int (default 0) — vertical bbox adjustment
    WS   /stream  -> STUB. Real-time inference wrapping is TODO.

Implementation note: MuseTalk's inference is a CLI (`scripts.inference`) that
expects a yaml config and writes to a result dir. We invoke it as a subprocess
per request, in the cloned repo root (`/app/MuseTalk`). The running container
holds the models/ in an overlay bind-mount at `/app/MuseTalk/models`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import yaml  # PyYAML ships with MuseTalk's requirements, and we also add it explicitly.
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger("avatar")
logging.basicConfig(level=logging.INFO)

REPO_DIR = Path(os.environ.get("MUSETALK_REPO_DIR", "/app/MuseTalk"))
MODELS_DIR = Path(os.environ.get("MUSETALK_MODELS_DIR", "/app/MuseTalk/models"))
VERSION = os.environ.get("MUSETALK_VERSION", "v15")  # v15 = MuseTalk 1.5
DEVICE = os.environ.get("MUSETALK_DEVICE", "cuda")

# Weights presence flag — set once download_weights.sh has successfully run.
_WEIGHT_MARKER = MODELS_DIR / "musetalkV15" / "unet.pth"

app = FastAPI(title="LangTutor Avatar (MuseTalk v1.5)")


def _weights_ready() -> bool:
    return _WEIGHT_MARKER.exists()


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok" if _weights_ready() else "models-missing",
            "weights": str(_WEIGHT_MARKER),
            "version": VERSION,
            "device": DEVICE,
        }
    )


def _run_musetalk(
    audio_path: Path,
    source_path: Path,
    output_dir: Path,
    bbox_shift: int = 0,
) -> Path:
    """Invoke MuseTalk's inference script; return the path to the generated MP4."""
    if not _weights_ready():
        raise RuntimeError(
            f"MuseTalk weights not found at {_WEIGHT_MARKER}. "
            "Container entrypoint should run download_weights.sh on first boot."
        )

    # Build a per-request yaml config.
    config = {
        "task_0": {
            "video_path": str(source_path),
            "audio_path": str(audio_path),
            "bbox_shift": int(bbox_shift),
        }
    }
    config_path = output_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    if VERSION == "v15":
        model_dir = MODELS_DIR / "musetalkV15"
        unet_path = model_dir / "unet.pth"
        version_arg = "v15"
    else:
        model_dir = MODELS_DIR / "musetalk"
        unet_path = model_dir / "pytorch_model.bin"
        version_arg = "v1"

    cmd = [
        "python", "-m", "scripts.inference",
        "--inference_config", str(config_path),
        "--result_dir", str(output_dir),
        "--unet_model_path", str(unet_path),
        "--unet_config", str(model_dir / "musetalk.json"),
        "--version", version_arg,
        "--whisper_dir", str(MODELS_DIR / "whisper"),
    ]
    logger.info("running: %s (cwd=%s)", " ".join(cmd), REPO_DIR)

    proc = subprocess.run(
        cmd,
        cwd=str(REPO_DIR),
        capture_output=True,
        text=True,
        timeout=600,  # 10 min hard cap
    )
    if proc.returncode != 0:
        logger.error("musetalk stderr:\n%s", proc.stderr[-4000:])
        raise RuntimeError(
            f"MuseTalk inference failed (exit {proc.returncode}). "
            f"Last stderr: {proc.stderr[-500:]}"
        )

    # MuseTalk writes the result as task_0.mp4 under result_dir/<video-name>/
    # or directly under result_dir. Find the newest MP4.
    candidates = sorted(output_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise RuntimeError(f"MuseTalk produced no MP4 in {output_dir}")
    return candidates[0]


@app.post("/render")
async def render(
    audio: UploadFile = File(...),
    source: UploadFile = File(...),
    bbox_shift: int = Form(0),
) -> Response:
    """One-shot audio + source -> MP4 with lip-sync."""
    # Working dir for this request.
    workdir = Path(tempfile.mkdtemp(prefix=f"musetalk-{uuid.uuid4().hex[:8]}-"))
    try:
        audio_ext = Path(audio.filename or "a.wav").suffix or ".wav"
        src_ext = Path(source.filename or "s.mp4").suffix or ".mp4"
        audio_path = workdir / f"audio{audio_ext}"
        source_path = workdir / f"source{src_ext}"

        audio_path.write_bytes(await audio.read())
        source_path.write_bytes(await source.read())

        def _run() -> Path:
            return _run_musetalk(audio_path, source_path, workdir, bbox_shift=bbox_shift)

        try:
            mp4 = await asyncio.get_event_loop().run_in_executor(None, _run)
        except Exception as exc:  # noqa: BLE001
            logger.exception("render failed")
            return JSONResponse({"error": str(exc)}, status_code=500)

        video_bytes = mp4.read_bytes()
        return Response(content=video_bytes, media_type="video/mp4")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@app.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    """Real-time streaming — not implemented yet.

    MuseTalk has a realtime mode (`scripts.realtime_inference`) designed to
    produce video chunks as audio arrives. Wiring that up needs a persistent
    worker and a chunked frame-encoding path. For now this endpoint simply
    closes the connection with an informational reason.
    """
    await ws.accept()
    try:
        await ws.send_json(
            {
                "error": "streaming_not_implemented",
                "hint": "Use POST /render for one-shot audio+source -> mp4.",
            }
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        await ws.close(code=1011)
    except Exception:  # noqa: BLE001
        pass


@app.on_event("startup")
async def _startup() -> None:
    logger.info(
        "avatar startup: repo=%s models=%s weights_present=%s",
        REPO_DIR, MODELS_DIR, _weights_ready(),
    )
