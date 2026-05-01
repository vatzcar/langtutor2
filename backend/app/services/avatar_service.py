"""HTTP client for the MuseTalk avatar service.

The avatar service exposes both a synchronous `/render` (await-and-return-MP4)
and a queued `/render_async` + `/jobs/{id}` flow. Phase 2's persistent worker
makes both fast — no per-request model load — but the queued flow is the right
path for the agent worker because it returns immediately and lets the caller
poll while the GPU works on a previous job.

Phase 3 will replace HTTP polling with a streaming socket; until then this
client is the supported integration surface.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AvatarServiceError(RuntimeError):
    """Raised when the avatar service returns a non-success response."""


async def render_sync(
    audio_path: Path,
    source_path: Path,
    bbox_shift: int = 0,
    timeout_s: float = 300.0,
) -> bytes:
    """Synchronous render — POST audio + source, await the MP4."""
    url = f"{settings.avatar_base_url}/render"
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
        with open(audio_path, "rb") as af, open(source_path, "rb") as sf:
            resp = await client.post(
                url,
                files={
                    "audio": (audio_path.name, af, "audio/wav"),
                    "source": (source_path.name, sf, "video/mp4"),
                },
                data={"bbox_shift": str(bbox_shift)},
            )
    if resp.status_code != 200:
        raise AvatarServiceError(
            f"avatar /render failed ({resp.status_code}): {resp.text[:500]}"
        )
    return resp.content


async def render_async_submit(
    audio_path: Path,
    source_path: Path,
    bbox_shift: int = 0,
) -> str:
    """Queue a render. Returns a job_id."""
    url = f"{settings.avatar_base_url}/render_async"
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        with open(audio_path, "rb") as af, open(source_path, "rb") as sf:
            resp = await client.post(
                url,
                files={
                    "audio": (audio_path.name, af, "audio/wav"),
                    "source": (source_path.name, sf, "video/mp4"),
                },
                data={"bbox_shift": str(bbox_shift)},
            )
    if resp.status_code not in (200, 202):
        raise AvatarServiceError(
            f"avatar /render_async failed ({resp.status_code}): {resp.text[:500]}"
        )
    return resp.json()["job_id"]


async def render_async_poll(
    job_id: str,
    poll_interval_s: float = 0.5,
    timeout_s: float = 300.0,
) -> bytes:
    """Poll /jobs/{id} until ready; return the MP4 bytes. Deletes the job after."""
    url = f"{settings.avatar_base_url}/jobs/{job_id}"
    deadline = asyncio.get_event_loop().time() + timeout_s
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        while True:
            resp = await client.get(url)
            ctype = resp.headers.get("content-type", "")
            if resp.status_code == 200 and ctype.startswith("video/"):
                content = resp.content
                # Best-effort cleanup on the avatar service.
                try:
                    await client.delete(url)
                except Exception:  # noqa: BLE001
                    pass
                return content
            if resp.status_code == 200:
                payload = resp.json()
                status = payload.get("status")
                if status in {"pending", "running"}:
                    if asyncio.get_event_loop().time() > deadline:
                        raise AvatarServiceError(
                            f"avatar job {job_id} timed out in status={status}"
                        )
                    await asyncio.sleep(poll_interval_s)
                    continue
            if resp.status_code == 500:
                raise AvatarServiceError(
                    f"avatar job {job_id} failed: {resp.text[:500]}"
                )
            raise AvatarServiceError(
                f"avatar /jobs/{job_id} unexpected response ({resp.status_code}): "
                f"{resp.text[:500]}"
            )


async def render_via_queue(
    audio_path: Path,
    source_path: Path,
    bbox_shift: int = 0,
    timeout_s: float = 300.0,
) -> bytes:
    """Submit + poll convenience helper."""
    job_id = await render_async_submit(audio_path, source_path, bbox_shift)
    return await render_async_poll(job_id, timeout_s=timeout_s)


async def health() -> dict:
    """GET /health — useful for readiness probes and tests."""
    url = f"{settings.avatar_base_url}/health"
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise AvatarServiceError(
            f"avatar /health failed ({resp.status_code}): {resp.text[:200]}"
        )
    return resp.json()
