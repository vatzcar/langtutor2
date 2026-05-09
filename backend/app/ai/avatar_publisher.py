"""LiveKit video-track publisher for the avatar pipeline.

Connects to a LiveKit room (same participant as the VoiceAssistant) and
publishes a ``VideoTrack`` that shows:

* **Idle state** — looping pre-rendered frames from the persona's idle-loop MP4.
* **Speaking state** — lip-synced frames streamed from the MuseTalk avatar
  service via the ``/stream`` WebSocket.

Usage from the agent worker::

    publisher = AvatarPublisher(room, avatar_ws_url, idle_video_path)
    await publisher.start()
    ...
    await publisher.render_speech(audio_wav_bytes, source_path)
    ...
    await publisher.stop()
"""

from __future__ import annotations

import asyncio
import json
import logging
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from livekit import rtc

logger = logging.getLogger(__name__)

AVATAR_VIDEO_WIDTH = 512
AVATAR_VIDEO_HEIGHT = 512
DEFAULT_FPS = 25


def _load_idle_frames(video_path: Path, width: int, height: int) -> tuple[list[np.ndarray], int]:
    """Extract frames from an MP4 via ffmpeg pipe. Returns (frames_rgba, fps)."""
    probe_cmd = [
        "ffmpeg", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "csv=p=0", "-i", str(video_path),
    ]
    fps = DEFAULT_FPS
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0",
             str(video_path)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "/" in result.stdout.strip():
            num, den = result.stdout.strip().split("/")
            fps = int(num) // max(int(den), 1)
    except Exception:  # noqa: BLE001
        pass

    cmd = [
        "ffmpeg", "-v", "error",
        "-i", str(video_path),
        "-vf", f"scale={width}:{height}",
        "-pix_fmt", "rgba",
        "-f", "rawvideo",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {proc.stderr[:500]}")

    raw = proc.stdout
    frame_size = width * height * 4  # RGBA
    frame_count = len(raw) // frame_size
    frames = []
    for i in range(frame_count):
        buf = raw[i * frame_size : (i + 1) * frame_size]
        frames.append(np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4))
    return frames, fps


class AvatarPublisher:
    """Publishes avatar video frames to a LiveKit room."""

    def __init__(
        self,
        room: rtc.Room,
        avatar_ws_url: str,
        idle_video_path: Optional[Path] = None,
        width: int = AVATAR_VIDEO_WIDTH,
        height: int = AVATAR_VIDEO_HEIGHT,
    ) -> None:
        self._room = room
        self._avatar_ws_url = avatar_ws_url.rstrip("/")
        self._idle_video_path = idle_video_path
        self._width = width
        self._height = height
        self._fps = DEFAULT_FPS
        self._source: Optional[rtc.VideoSource] = None
        self._track: Optional[rtc.LocalVideoTrack] = None
        self._idle_task: Optional[asyncio.Task] = None
        self._rendering = asyncio.Event()
        self._stopped = False
        self._idle_frames: list[np.ndarray] = []

    async def start(self) -> None:
        """Publish a video track and start the idle loop."""
        self._source = rtc.VideoSource(self._width, self._height)
        self._track = rtc.LocalVideoTrack.create_video_track("avatar", self._source)
        opts = rtc.TrackPublishOptions()
        opts.source = rtc.TrackSource.SOURCE_CAMERA
        await self._room.local_participant.publish_track(self._track, opts)
        logger.info("avatar video track published (%dx%d)", self._width, self._height)

        if self._idle_video_path and self._idle_video_path.exists():
            loop = asyncio.get_event_loop()
            self._idle_frames, self._fps = await loop.run_in_executor(
                None, _load_idle_frames, self._idle_video_path, self._width, self._height,
            )
            logger.info(
                "loaded %d idle frames at %d fps from %s",
                len(self._idle_frames), self._fps, self._idle_video_path,
            )

        self._idle_task = asyncio.ensure_future(self._idle_loop())

    def _push_frame(self, rgba: np.ndarray) -> None:
        if self._source is None:
            return
        frame = rtc.VideoFrame(
            width=rgba.shape[1],
            height=rgba.shape[0],
            type=rtc.VideoBufferType.RGBA,
            data=rgba.tobytes(),
        )
        self._source.capture_frame(frame)

    async def _idle_loop(self) -> None:
        """Cycle through idle-loop frames when not rendering speech."""
        if not self._idle_frames:
            black = np.zeros((self._height, self._width, 4), dtype=np.uint8)
            black[:, :, 3] = 255  # opaque black
            while not self._stopped:
                if self._rendering.is_set():
                    await asyncio.sleep(0.05)
                    continue
                self._push_frame(black)
                await asyncio.sleep(1.0 / self._fps)
            return

        idx = 0
        interval = 1.0 / self._fps
        while not self._stopped:
            if self._rendering.is_set():
                await asyncio.sleep(0.05)
                continue
            self._push_frame(self._idle_frames[idx % len(self._idle_frames)])
            idx += 1
            await asyncio.sleep(interval)

    async def render_speech(self, audio_wav: bytes, source_path: str) -> None:
        """Send audio to the avatar service and stream lip-synced frames.

        Pauses the idle loop, streams JPEG frames from the ``/stream``
        WebSocket, pushes each to the VideoSource, then resumes idle.
        """
        import websockets

        self._rendering.set()
        ws_url = self._avatar_ws_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/stream"
        try:
            async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
                await ws.send(json.dumps({
                    "source_path": source_path,
                    "bbox_shift": 0,
                }))
                await ws.send(audio_wav)

                interval = 1.0 / self._fps
                while True:
                    msg = await ws.recv()
                    if isinstance(msg, str):
                        data = json.loads(msg)
                        if data.get("fps"):
                            interval = 1.0 / data["fps"]
                        if data.get("type") in ("done", "error"):
                            if data.get("type") == "error":
                                logger.error("avatar stream error: %s", data.get("error"))
                            break
                    else:
                        rgba = _jpeg_to_rgba(msg, self._width, self._height)
                        if rgba is not None:
                            self._push_frame(rgba)
                            await asyncio.sleep(interval)
        except Exception:  # noqa: BLE001
            logger.exception("render_speech failed")
        finally:
            self._rendering.clear()

    async def stop(self) -> None:
        """Disconnect video track and cancel background tasks."""
        self._stopped = True
        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
            try:
                await self._idle_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self._track:
            try:
                await self._room.local_participant.unpublish_track(self._track.sid)
            except Exception:  # noqa: BLE001
                pass
        self._idle_frames.clear()
        logger.info("avatar publisher stopped")


def _jpeg_to_rgba(jpeg_bytes: bytes, width: int, height: int) -> Optional[np.ndarray]:
    """Decode JPEG to RGBA numpy array, resizing to target dimensions."""
    try:
        import cv2
        bgr = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            return None
        bgr = cv2.resize(bgr, (width, height))
        rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
        return rgba
    except ImportError:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGBA").resize((width, height))
        return np.array(img)
