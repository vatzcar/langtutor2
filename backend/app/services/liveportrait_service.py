"""HTTP client for the LivePortrait service + background idle-loop job runner."""

import logging
import shutil
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.models.persona import Persona

logger = logging.getLogger(__name__)

IDLE_LOOP_DIR = Path(settings.upload_dir) / "idle_loops"


async def render_idle_loop(source_image_path: Path) -> bytes:
    """POST the persona's portrait to the LivePortrait service, return MP4 bytes."""
    url = f"{settings.liveportrait_base_url}/render"
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        with open(source_image_path, "rb") as f:
            resp = await client.post(
                url,
                files={"source_image": (source_image_path.name, f, "image/png")},
            )
    if resp.status_code != 200:
        raise RuntimeError(f"LivePortrait render failed ({resp.status_code}): {resp.text[:500]}")
    return resp.content


async def run_idle_loop_job(persona_id: UUID) -> None:
    """Background task: render idle loop for a persona, save MP4, update DB row."""
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                select(Persona.image_url).where(Persona.id == persona_id)
            )
            row = result.one_or_none()

        if row is None or not row.image_url:
            logger.warning("Persona %s not found or has no image_url, skipping idle loop", persona_id)
            return

        image_path = Path(row.image_url.lstrip("/"))
        if not image_path.exists():
            logger.error("Portrait file missing: %s", image_path)
            return

        logger.info("Starting idle-loop render for persona %s", persona_id)
        mp4_bytes = await render_idle_loop(image_path)

        IDLE_LOOP_DIR.mkdir(parents=True, exist_ok=True)
        output_path = IDLE_LOOP_DIR / f"{persona_id}.mp4"
        output_path.write_bytes(mp4_bytes)

        idle_video_url = f"/uploads/idle_loops/{persona_id}.mp4"
        async with engine.begin() as conn:
            await conn.execute(
                update(Persona)
                .where(Persona.id == persona_id)
                .values(idle_video_url=idle_video_url)
            )

        logger.info("Idle loop ready for persona %s → %s", persona_id, idle_video_url)

    except Exception:
        logger.exception("Idle-loop render failed for persona %s", persona_id)
    finally:
        await engine.dispose()


def enqueue_idle_loop_render(persona_id: UUID) -> None:
    """Fire-and-forget: schedule an idle-loop render as a background task.

    Called from persona_service after a portrait is set or changed.
    Uses asyncio to run the job without blocking the request.
    """
    import asyncio

    async def _wrapper():
        try:
            await run_idle_loop_job(persona_id)
        except Exception:
            logger.exception("Idle-loop background job crashed for %s", persona_id)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_wrapper())
    except RuntimeError:
        asyncio.run(_wrapper())
