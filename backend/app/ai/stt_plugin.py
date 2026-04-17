"""Faster-Whisper STT plugin for LiveKit Agents.

Talks to a self-hosted `fedirz/faster-whisper-server` instance over its
OpenAI-compatible REST endpoint at ``POST /v1/audio/transcriptions``.

Streaming design: we buffer audio frames until ~500 ms of speech has
accumulated (configurable), POST the buffer as WAV to the server, and
emit the transcript. This is NOT low-latency streaming — for that we
would use the server's WebSocket endpoint. A REST-based chunker is
deliberately chosen here for simplicity; swap in a WebSocket client
once the v2 API stabilises.
"""

from __future__ import annotations

import asyncio
import io
import logging
import struct
import wave
from dataclasses import dataclass
from typing import AsyncIterable, Optional

import httpx
from livekit import rtc
from livekit.agents import stt, utils

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "Systran/faster-whisper-base.en"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHUNK_MS = 500


@dataclass
class FasterWhisperSTTOptions:
    base_url: str = "http://localhost:8010"
    model: str = DEFAULT_MODEL
    language: Optional[str] = None
    sample_rate: int = DEFAULT_SAMPLE_RATE
    chunk_ms: int = DEFAULT_CHUNK_MS
    request_timeout: float = 15.0


class FasterWhisperSTT(stt.STT):
    """LiveKit STT backed by faster-whisper-server REST API."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8010",
        model: str = DEFAULT_MODEL,
        language: Optional[str] = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        chunk_ms: int = DEFAULT_CHUNK_MS,
    ) -> None:
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=False,
            )
        )
        self._opts = FasterWhisperSTTOptions(
            base_url=base_url.rstrip("/"),
            model=model,
            language=language,
            sample_rate=sample_rate,
            chunk_ms=chunk_ms,
        )
        self._client = httpx.AsyncClient(timeout=self._opts.request_timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def recognize(
        self,
        *,
        buffer: utils.AudioBuffer,
        language: Optional[str] = None,
    ) -> stt.SpeechEvent:
        """One-shot recognition over a completed buffer."""
        wav_bytes = _pcm_to_wav(buffer.data, buffer.sample_rate)
        text = await self._transcribe(wav_bytes, language or self._opts.language)
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=text, language=language or "en")],
        )

    def stream(
        self,
        *,
        language: Optional[str] = None,
    ) -> "_FasterWhisperStream":
        return _FasterWhisperStream(
            stt_impl=self,
            opts=self._opts,
            language=language or self._opts.language,
        )

    async def _transcribe(self, wav_bytes: bytes, language: Optional[str]) -> str:
        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        data = {"model": self._opts.model}
        if language:
            data["language"] = language
        url = f"{self._opts.base_url}/v1/audio/transcriptions"
        try:
            resp = await self._client.post(url, data=data, files=files)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("faster-whisper request failed: %s", exc)
            return ""
        payload = resp.json()
        return (payload.get("text") or "").strip()


class _FasterWhisperStream(stt.SpeechStream):
    """Chunk-based streaming — buffers audio then posts to REST API."""

    def __init__(
        self,
        *,
        stt_impl: FasterWhisperSTT,
        opts: FasterWhisperSTTOptions,
        language: Optional[str],
    ) -> None:
        super().__init__()
        self._stt = stt_impl
        self._opts = opts
        self._language = language
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        chunk_bytes_target = int(
            self._opts.sample_rate * 2 * self._opts.chunk_ms / 1000
        )
        pcm_buffer = bytearray()
        try:
            async for frame in self._input_ch:
                if isinstance(frame, rtc.AudioFrame):
                    pcm_buffer.extend(frame.data.tobytes())
                    if len(pcm_buffer) >= chunk_bytes_target:
                        await self._flush(bytes(pcm_buffer))
                        pcm_buffer.clear()
            # End-of-stream flush.
            if pcm_buffer:
                await self._flush(bytes(pcm_buffer))
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("FasterWhisperStream crashed")

    async def _flush(self, pcm: bytes) -> None:
        wav = _pcm_to_wav_raw(pcm, self._opts.sample_rate)
        text = await self._stt._transcribe(wav, self._language)
        if text:
            self._event_ch.send_nowait(
                stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[stt.SpeechData(text=text, language=self._language or "en")],
                )
            )

    async def aclose(self) -> None:
        self._task.cancel()
        try:
            await self._task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass


def _pcm_to_wav(audio_data, sample_rate: int) -> bytes:
    """Encode a LiveKit AudioBuffer payload to WAV."""
    raw = audio_data.tobytes() if hasattr(audio_data, "tobytes") else bytes(audio_data)
    return _pcm_to_wav_raw(raw, sample_rate)


def _pcm_to_wav_raw(pcm: bytes, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # int16
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buf.getvalue()
