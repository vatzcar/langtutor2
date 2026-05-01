"""LivePortrait FastAPI shim — generates idle-motion MP4 from a portrait image."""

import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger("liveportrait")
logging.basicConfig(level=logging.INFO)

REPO_DIR = Path(os.environ.get("LIVEPORTRAIT_REPO_DIR", "/app/LivePortrait"))
MODELS_DIR = Path(os.environ.get("LIVEPORTRAIT_MODELS_DIR", "/app/LivePortrait/pretrained_weights"))
DEVICE = os.environ.get("LIVEPORTRAIT_DEVICE", "cuda")
CHECKPOINT_DIR = Path(os.environ.get("LIVEPORTRAIT_CHECKPOINT_DIR", "/app/checkpoints"))

DRIVING_VIDEO = CHECKPOINT_DIR / "liveportrait" / "idle_driving" / "idle_motion_reference.mp4"
_WEIGHT_MARKER = MODELS_DIR / "liveportrait" / "base_models" / "appearance_feature_extractor.pth"

app = FastAPI(title="LangTutor LivePortrait")


def _weights_ready() -> bool:
    return _WEIGHT_MARKER.exists() and _WEIGHT_MARKER.stat().st_size > 0


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok" if _weights_ready() else "models-missing",
        "weights": str(_WEIGHT_MARKER),
        "driving_video": str(DRIVING_VIDEO),
        "driving_video_present": DRIVING_VIDEO.exists(),
        "device": DEVICE,
    })


def _run_liveportrait(source_image: Path, driving_video: Path, output_dir: Path) -> Path:
    if not _weights_ready():
        raise RuntimeError("LivePortrait weights not found")
    if not driving_video.exists():
        raise RuntimeError(f"Driving video not found: {driving_video}")

    cmd = [
        "python", "-m", "inference",
        "--source_image", str(source_image),
        "--driving_info", str(driving_video),
        "--output_dir", str(output_dir),
        "--device_id", "0",
        "--flag_pasteback",
        "--flag_do_crop",
    ]

    logger.info("Running LivePortrait: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=str(REPO_DIR),
        capture_output=True,
        text=True,
        timeout=600,
    )

    if result.returncode != 0:
        logger.error("LivePortrait stderr: %s", result.stderr[-2000:] if result.stderr else "(empty)")
        raise RuntimeError(f"LivePortrait exited with code {result.returncode}")

    mp4s = sorted(output_dir.glob("**/*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        raise RuntimeError("No output MP4 found after LivePortrait inference")
    return mp4s[0]


@app.post("/render")
async def render(
    source_image: UploadFile = File(...),
    driving_video: UploadFile | None = File(None),
):
    import asyncio
    loop = asyncio.get_event_loop()

    request_id = uuid.uuid4().hex[:12]
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"lp_{request_id}_"))

    try:
        src_ext = Path(source_image.filename).suffix if source_image.filename else ".png"
        src_path = tmp_dir / f"source{src_ext}"
        with open(src_path, "wb") as f:
            shutil.copyfileobj(source_image.file, f)

        if driving_video is not None:
            drv_ext = Path(driving_video.filename).suffix if driving_video.filename else ".mp4"
            drv_path = tmp_dir / f"driving{drv_ext}"
            with open(drv_path, "wb") as f:
                shutil.copyfileobj(driving_video.file, f)
        else:
            drv_path = DRIVING_VIDEO

        out_dir = tmp_dir / "output"
        out_dir.mkdir()

        output_mp4 = await loop.run_in_executor(
            None, _run_liveportrait, src_path, drv_path, out_dir
        )

        video_bytes = output_mp4.read_bytes()
        return Response(content=video_bytes, media_type="video/mp4")

    except Exception as e:
        logger.exception("Render failed: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.on_event("startup")
async def _startup() -> None:
    logger.info(
        "liveportrait startup: repo=%s models=%s weights_present=%s driving_video=%s",
        REPO_DIR, MODELS_DIR, _weights_ready(), DRIVING_VIDEO.exists(),
    )
