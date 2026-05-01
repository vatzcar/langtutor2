"""FastAPI shim around TMElyralab/MuseTalk (v1.5).

MuseTalk does audio-driven talking-head video: given a source video (or image)
of a person's face + a WAV of speech, it produces an MP4 with lip-sync'd face.

Endpoints:
    GET  /health
    POST /render         (multipart) -> video/mp4    -- synchronous
    POST /render_async   (multipart) -> {"job_id"}   -- queued; poll /jobs/{id}
    GET  /jobs/{job_id}                              -- pending|ready|failed (+ MP4)
    WS   /stream  -> STUB. Real-time inference wrapping is Phase 3.

Phase 2 of Path 4: the heavy MuseTalk model state (UNet, VAE, Whisper,
FaceParsing) is loaded **once** at FastAPI startup via `MuseTalkWorker` and
serviced by an in-process asyncio queue. Previous behaviour spawned
`python -m scripts.inference` per request and paid ~60–90 s of model-load
cost every time. The worker is shared across requests; the queue runs one
job at a time (single GPU, single inference process — concurrency at the
*frame* level lands in Phase 3).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse, JSONResponse, Response

from worker import MuseTalkWorker  # noqa: E402  -- loaded lazily

logger = logging.getLogger("avatar")
logging.basicConfig(level=logging.INFO)

REPO_DIR = Path(os.environ.get("MUSETALK_REPO_DIR", "/app/MuseTalk"))
MODELS_DIR = Path(os.environ.get("MUSETALK_MODELS_DIR", "/app/MuseTalk/models"))
VERSION = os.environ.get("MUSETALK_VERSION", "v15")
DEVICE = os.environ.get("MUSETALK_DEVICE", "cuda")
USE_FP16 = os.environ.get("MUSETALK_FP16", "1") not in {"0", "false", "False", ""}
PRELOAD_DIR = Path(os.environ.get("MUSETALK_PRELOAD_DIR", "/app/preload"))

# Weights presence flag — set once download_weights.sh has successfully run.
_WEIGHT_MARKER = MODELS_DIR / "musetalkV15" / "unet.pth"

app = FastAPI(title="LangTutor Avatar (MuseTalk v1.5)")


def _weights_ready() -> bool:
    return _WEIGHT_MARKER.exists()


# --------------------------------------------------------------------- state

@dataclass
class _Job:
    id: str
    audio_path: Path
    source_path: Path
    bbox_shift: int
    workdir: Path
    future: asyncio.Future
    status: str = "pending"  # pending | running | ready | failed
    result_path: Optional[Path] = None
    error: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


class _AppState:
    worker: Optional[MuseTalkWorker] = None
    worker_error: Optional[str] = None
    queue: Optional[asyncio.Queue] = None
    runner_task: Optional[asyncio.Task] = None
    jobs: dict[str, _Job] = {}


state = _AppState()


# ----------------------------------------------------------------- lifecycle

@app.on_event("startup")
async def _startup() -> None:
    logger.info(
        "avatar startup: repo=%s models=%s weights_present=%s",
        REPO_DIR, MODELS_DIR, _weights_ready(),
    )
    state.queue = asyncio.Queue()
    state.runner_task = asyncio.create_task(_queue_runner())

    # MuseTalk's load_all_model resolves VAE/etc. via paths relative to cwd
    # (e.g. "models/sd-vae"). The repo expects to *be* the cwd. Match that.
    if REPO_DIR.is_dir():
        try:
            os.chdir(REPO_DIR)
        except OSError as exc:  # noqa: BLE001
            logger.warning("chdir to %s failed: %s", REPO_DIR, exc)

    if not _weights_ready():
        state.worker_error = (
            f"weights missing at {_WEIGHT_MARKER}; entrypoint must run "
            "download_weights.sh before /render becomes available"
        )
        logger.warning(state.worker_error)
        return

    # Build the worker on a thread so startup doesn't block the event loop
    # while torch loads ~1 GB of weights into VRAM (~30–60 s on a 4090).
    loop = asyncio.get_event_loop()

    def _build() -> MuseTalkWorker:
        if VERSION == "v15":
            model_dir = MODELS_DIR / "musetalkV15"
            unet_path = model_dir / "unet.pth"
        else:
            model_dir = MODELS_DIR / "musetalk"
            unet_path = model_dir / "pytorch_model.bin"
        return MuseTalkWorker(
            unet_model_path=unet_path,
            unet_config=model_dir / "musetalk.json",
            whisper_dir=MODELS_DIR / "whisper",
            version=VERSION,
            device=DEVICE,
            use_float16=USE_FP16,
        )

    try:
        state.worker = await loop.run_in_executor(None, _build)
        logger.info("MuseTalk worker initialised")
    except Exception as exc:  # noqa: BLE001
        state.worker_error = f"worker init failed: {exc!r}"
        logger.exception("MuseTalk worker init failed")
        return

    # Optional warm-up: if PRELOAD_DIR contains MP4s (one per persona idle
    # loop), prime the source-frame cache. Big steady-state latency win.
    if PRELOAD_DIR.is_dir():
        for src in sorted(PRELOAD_DIR.glob("*.mp4")):
            await loop.run_in_executor(None, state.worker.preload_source, src)


@app.on_event("shutdown")
async def _shutdown() -> None:
    if state.runner_task and not state.runner_task.done():
        state.runner_task.cancel()
        try:
            await state.runner_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass


async def _queue_runner() -> None:
    """Single-consumer pump. One job at a time on the GPU."""
    assert state.queue is not None
    loop = asyncio.get_event_loop()
    while True:
        job: _Job = await state.queue.get()
        if state.worker is None:
            err = state.worker_error or "worker unavailable"
            job.status = "failed"
            job.error = err
            if not job.future.done():
                job.future.set_exception(RuntimeError(err))
            continue

        job.status = "running"
        try:
            def _run() -> Path:
                return state.worker.infer(  # type: ignore[union-attr]
                    audio_path=job.audio_path,
                    source_path=job.source_path,
                    output_dir=job.workdir,
                    bbox_shift=job.bbox_shift,
                )
            result = await loop.run_in_executor(None, _run)
            job.result_path = result
            job.status = "ready"
            if not job.future.done():
                job.future.set_result(result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("job %s failed", job.id)
            job.status = "failed"
            job.error = repr(exc)
            if not job.future.done():
                job.future.set_exception(exc)


# -------------------------------------------------------------------- routes

@app.get("/health")
async def health() -> JSONResponse:
    if state.worker is not None:
        worker_status = "ready"
    elif _weights_ready():
        worker_status = "loading"
    else:
        worker_status = "models-missing"
    queue_depth = state.queue.qsize() if state.queue is not None else 0
    return JSONResponse(
        {
            "status": "ok" if worker_status == "ready" else worker_status,
            "worker": worker_status,
            "worker_error": state.worker_error,
            "queue_depth": queue_depth,
            "weights": str(_WEIGHT_MARKER),
            "version": VERSION,
            "device": DEVICE,
            "fp16": USE_FP16,
        }
    )


async def _enqueue_render(
    audio: UploadFile,
    source: UploadFile,
    bbox_shift: int,
) -> _Job:
    if state.queue is None:
        raise HTTPException(status_code=503, detail="queue not initialised")

    job_id = uuid.uuid4().hex
    workdir = Path(tempfile.mkdtemp(prefix=f"musetalk-{job_id[:8]}-"))
    audio_ext = Path(audio.filename or "a.wav").suffix or ".wav"
    src_ext = Path(source.filename or "s.mp4").suffix or ".mp4"
    audio_path = workdir / f"audio{audio_ext}"
    source_path = workdir / f"source{src_ext}"
    audio_path.write_bytes(await audio.read())
    source_path.write_bytes(await source.read())

    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()
    job = _Job(
        id=job_id,
        audio_path=audio_path,
        source_path=source_path,
        bbox_shift=int(bbox_shift),
        workdir=workdir,
        future=future,
    )
    state.jobs[job_id] = job
    await state.queue.put(job)
    return job


@app.post("/render")
async def render(
    audio: UploadFile = File(...),
    source: UploadFile = File(...),
    bbox_shift: int = Form(0),
) -> Response:
    """Synchronous one-shot: enqueue, await, return MP4 bytes."""
    job = await _enqueue_render(audio, source, bbox_shift)
    try:
        result_path: Path = await job.future
        video_bytes = result_path.read_bytes()
        return Response(content=video_bytes, media_type="video/mp4")
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc), "job_id": job.id}, status_code=500)
    finally:
        # Hold onto the job record briefly so /jobs/{id} can still report
        # status, but free disk now since the bytes are already in-flight.
        shutil.rmtree(job.workdir, ignore_errors=True)
        state.jobs.pop(job.id, None)


@app.post("/render_async")
async def render_async(
    audio: UploadFile = File(...),
    source: UploadFile = File(...),
    bbox_shift: int = Form(0),
) -> JSONResponse:
    """Queue a render and return a job id. Poll /jobs/{id}."""
    job = await _enqueue_render(audio, source, bbox_shift)
    queue_depth = state.queue.qsize() if state.queue is not None else 0
    return JSONResponse(
        {"job_id": job.id, "status": job.status, "queue_depth": queue_depth},
        status_code=202,
    )


@app.get("/jobs/{job_id}")
async def job_status(job_id: str) -> Response:
    job = state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job_id")
    if job.status == "ready" and job.result_path is not None:
        return FileResponse(
            job.result_path,
            media_type="video/mp4",
            filename=f"{job_id}.mp4",
        )
    if job.status == "failed":
        return JSONResponse(
            {"job_id": job.id, "status": "failed", "error": job.error},
            status_code=500,
        )
    return JSONResponse({"job_id": job.id, "status": job.status})


@app.delete("/jobs/{job_id}")
async def job_delete(job_id: str) -> JSONResponse:
    """Free disk after a successful /jobs/{id} download."""
    job = state.jobs.pop(job_id, None)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job_id")
    shutil.rmtree(job.workdir, ignore_errors=True)
    return JSONResponse({"job_id": job_id, "deleted": True})


@app.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    """Real-time streaming — Phase 3 replaces this stub with a real protocol."""
    await ws.accept()
    try:
        await ws.send_json(
            {
                "error": "streaming_not_implemented",
                "hint": "Use POST /render or /render_async for one-shot mode.",
            }
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        await ws.close(code=1011)
    except Exception:  # noqa: BLE001
        pass
