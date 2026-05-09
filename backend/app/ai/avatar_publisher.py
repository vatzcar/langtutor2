"""LiveKit video-track publisher backed by the MuseTalk avatar service.

Connects to the avatar service's ``/stream`` WebSocket, sends TTS audio,
receives JPEG frames, and pushes them into a LiveKit ``VideoSource`` so
the learner sees a talking-head avatar in their room.

Between utterances the publisher loops through idle-animation frames
(the persona's pre-rendered LivePortrait idle loop) so the avatar
never freezes.

Lifecycle (managed by the agent worker):
    publisher = AvatarPublisher(room, avatar_ws_url, idle_video_path)
    await publisher.start()          # connects WS, loads idle loop, publishes track
    await publisher.send_audio(wav)  # TTS utterance → lip-sync frames
    await publisher.stop()           # disconnects, unpublishes
"""

from __future__ import annotations

import asyncio
import io
import logging
import struct
import time
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]

from livekit import rtc

logger = logging.getLogger(__name__)

IDLE_TARGET_FPS = 25
JPEG_QUALITY = 85


class AvatarPublisher:
    """Manages a LiveKit video track backed by avatar-service frames."""

    def __init__(
        self,
        room: rtc.Room,
        avatar_ws_url: str,
        idle_video_path: Optional[Path] = None,
        width: int = 640,
        height: int = 480,
    ) -> None:
        self._room = room
        self._avatar_ws_url = avatar_ws_url
        self._idle_video_path = idle_video_path
        self._width = width
        self._height = height

        self._video_source: Optional[rtc.VideoSource] = None
        self._video_track: Optional[rtc.LocalVideoTrack] = None
        self._ws: Optional[object] = None  # websockets connection
        self._idle_frames: list[np.ndarray] = []
        self._idle_fps: int = IDLE_TARGET_FPS
        self._idle_task: Optional[asyncio.Task] = None
        self._speaking = False
        self._started = False
        self._source_sent = False

    async def start(self) -> None:
        """Connect to avatar service, load idle loop, publish video track."""
        if self._started:
            return

        # Load idle loop frames if available
        if self._idle_video_path and self._idle_video_path.exists() and cv2 is not None:
            await asyncio.get_event_loop().run_in_executor(None, self._load_idle_frames)

        # Create LiveKit video source and track
        self._video_source = rtc.VideoSource(self._width, self._height)
        self._video_track = rtc.LocalVideoTrack.create_video_track(
            "avatar", self._video_source,
        )
        await self._room.local_participant.publish_track(
            self._video_track,
            rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_CAMERA),
        )

        # Connect to avatar service WebSocket
        await self._connect_ws()

        # Start idle loop playback
        if self._idle_frames:
            self._idle_task = asyncio.create_task(self._idle_loop())

        self._started = True
        logger.info("avatar publisher started (idle_frames=%d)", len(self._idle_frames))

    async def stop(self) -> None:
        """Disconnect and clean up."""
        self._started = False

        if self._idle_task and not self._idle_task.done():
            self._idle_task.cancel()
            try:
                await self._idle_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

        if self._ws is not None:
            try:
                import websockets
                await self._ws.send('{"type": "close"}')
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None

        if self._video_track is not None:
            try:
                await self._room.local_participant.unpublish_track(
                    self._video_track.sid,
                )
            except Exception:  # noqa: BLE001
                pass

        logger.info("avatar publisher stopped")

    async def send_audio(self, audio_wav_bytes: bytes) -> None:
        """Send a TTS utterance to the avatar service and stream frames."""
        if self._ws is None:
            logger.warning("avatar WS not connected, skipping send_audio")
            return

        self._speaking = True
        try:
            import websockets
            import json

            # Send audio message
            await self._ws.send(json.dumps({"type": "audio"}))
            await self._ws.send(audio_wav_bytes)

            # Receive frames until "done"
            fps = self._idle_fps or IDLE_TARGET_FPS
            frame_interval = 1.0 / fps

            while True:
                msg = await self._ws.recv()
                if isinstance(msg, bytes):
                    # JPEG frame — decode and push to video source
                    self._push_jpeg_frame(msg)
                    await asyncio.sleep(frame_interval)
                elif isinstance(msg, str):
                    data = json.loads(msg)
                    if data.get("type") == "done":
                        break
                    if data.get("type") == "error":
                        logger.error("avatar stream error: %s", data.get("message"))
                        break
        except Exception:  # noqa: BLE001
            logger.exception("send_audio failed")
        finally:
            self._speaking = False

    # ---------------------------------------------------------------- private

    async def _connect_ws(self) -> None:
        """Open WebSocket to avatar service and send source."""
        try:
            import websockets
            import json

            self._ws = await websockets.connect(
                self._avatar_ws_url, max_size=50 * 1024 * 1024,
            )

            # Send init + source bytes
            source_path = self._idle_video_path
            if source_path and source_path.exists():
                source_bytes = source_path.read_bytes()
                source_name = source_path.name
            else:
                # No idle loop — send a placeholder 1-pixel PNG
                source_bytes = self._make_placeholder_png()
                source_name = "placeholder.png"

            await self._ws.send(json.dumps({
                "type": "init",
                "source_name": source_name,
            }))
            await self._ws.send(source_bytes)

            # Wait for ready
            ready_msg = json.loads(await self._ws.recv())
            if ready_msg.get("type") == "ready":
                self._idle_fps = ready_msg.get("fps", IDLE_TARGET_FPS)
                logger.info("avatar WS ready, fps=%d", self._idle_fps)
                self._source_sent = True
            else:
                logger.error("avatar WS init failed: %s", ready_msg)
                await self._ws.close()
                self._ws = None
        except Exception:  # noqa: BLE001
            logger.exception("avatar WS connection failed")
            self._ws = None

    def _load_idle_frames(self) -> None:
        """Extract frames from the idle-loop MP4 into memory."""
        if cv2 is None:
            return
        cap = cv2.VideoCapture(str(self._idle_video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or IDLE_TARGET_FPS
        self._idle_fps = int(fps)
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            resized = cv2.resize(frame, (self._width, self._height))
            frames.append(resized)
        cap.release()
        self._idle_frames = frames
        logger.info("loaded %d idle frames at %d fps", len(frames), self._idle_fps)

    async def _idle_loop(self) -> None:
        """Continuously push idle-loop frames when not speaking."""
        idx = 0
        interval = 1.0 / self._idle_fps
        while True:
            if not self._speaking and self._idle_frames:
                frame = self._idle_frames[idx % len(self._idle_frames)]
                self._push_bgr_frame(frame)
                idx += 1
            await asyncio.sleep(interval)

    def _push_bgr_frame(self, bgr: np.ndarray) -> None:
        """Convert BGR numpy array to RGBA and push to VideoSource."""
        if self._video_source is None:
            return
        rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
        if rgba.shape[1] != self._width or rgba.shape[0] != self._height:
            rgba = cv2.resize(rgba, (self._width, self._height))
        frame = rtc.VideoFrame(
            width=self._width,
            height=self._height,
            type=rtc.VideoBufferType.RGBA,
            data=rgba.tobytes(),
        )
        self._video_source.capture_frame(frame)

    def _push_jpeg_frame(self, jpeg_bytes: bytes) -> None:
        """Decode JPEG and push to VideoSource."""
        if self._video_source is None or cv2 is None:
            return
        arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is not None:
            self._push_bgr_frame(bgr)

    @staticmethod
    def _make_placeholder_png() -> bytes:
        """1×1 black PNG for when no idle loop is available."""
        import struct as _struct
        import zlib
        raw = b"\x00\x00\x00\x00"
        compressed = zlib.compress(raw)
        def _chunk(ctype, data):
            c = ctype + data
            return _struct.pack(">I", len(data)) + c + _struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return (
            b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", _struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + _chunk(b"IDAT", compressed)
            + _chunk(b"IEND", b"")
        )
