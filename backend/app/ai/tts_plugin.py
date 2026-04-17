"""Fish-Speech TTS plugin for LiveKit Agents.

Calls the self-hosted Fish-Speech HTTP API at ``POST /v1/tts`` and emits
the returned audio as PCM frames on the LiveKit track.

The exact payload accepted by Fish-Speech has shifted across releases:
  - 1.4+:  {"text": ..., "reference_audio": b64, "reference_text": ...}
  - Older: {"text": ..., "speaker": "..."}
We send the modern shape and fall back to text-only if the server rejects
reference fields.
"""

from __future__ import annotations

import asyncio
import io
import logging
import wave
from dataclasses import dataclass
from typing import AsyncIterable, Optional

import httpx
from livekit import rtc
from livekit.agents import tts, utils

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_RATE = 24000
NUM_CHANNELS = 1


@dataclass
class FishSpeechTTSOptions:
    base_url: str = "http://localhost:8011"
    reference_audio_b64: Optional[str] = None
    reference_text: Optional[str] = None
    sample_rate: int = DEFAULT_SAMPLE_RATE
    request_timeout: float = 30.0


class FishSpeechTTS(tts.TTS):
    """LiveKit TTS implementation backed by Fish-Speech."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8011",
        reference_audio_b64: Optional[str] = None,
        reference_text: Optional[str] = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=NUM_CHANNELS,
        )
        self._opts = FishSpeechTTSOptions(
            base_url=base_url.rstrip("/"),
            reference_audio_b64=reference_audio_b64,
            reference_text=reference_text,
            sample_rate=sample_rate,
        )
        self._client = httpx.AsyncClient(timeout=self._opts.request_timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    def synthesize(self, text: str) -> "_FishSpeechChunkedStream":
        return _FishSpeechChunkedStream(tts_impl=self, text=text, opts=self._opts)

    async def _request(self, text: str) -> bytes:
        payload: dict = {"text": text}
        if self._opts.reference_audio_b64:
            payload["reference_audio"] = self._opts.reference_audio_b64
        if self._opts.reference_text:
            payload["reference_text"] = self._opts.reference_text

        url = f"{self._opts.base_url}/v1/tts"
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Retry without reference fields if server rejected them.
            if exc.response.status_code in (400, 422) and (
                "reference_audio" in payload or "reference_text" in payload
            ):
                logger.info("Retrying TTS without reference fields: %s", exc)
                resp = await self._client.post(url, json={"text": text})
                resp.raise_for_status()
            else:
                raise
        return resp.content


class _FishSpeechChunkedStream(tts.ChunkedStream):
    """Emits a single full utterance as LiveKit-friendly PCM frames."""

    def __init__(
        self,
        *,
        tts_impl: FishSpeechTTS,
        text: str,
        opts: FishSpeechTTSOptions,
    ) -> None:
        super().__init__()
        self._tts = tts_impl
        self._text = text
        self._opts = opts

    async def _main_task(self) -> None:
        audio_bytes = await self._tts._request(self._text)
        pcm, sample_rate = _decode_wav(audio_bytes, fallback_rate=self._opts.sample_rate)

        frame = rtc.AudioFrame(
            data=pcm,
            sample_rate=sample_rate,
            num_channels=NUM_CHANNELS,
            samples_per_channel=len(pcm) // 2,
        )
        self._event_ch.send_nowait(
            tts.SynthesizedAudio(
                request_id=utils.shortuuid(),
                frame=frame,
            )
        )


def _decode_wav(data: bytes, *, fallback_rate: int) -> tuple[bytes, int]:
    """Return (pcm16, sample_rate). Falls back to treating bytes as raw PCM."""
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            sample_rate = wav.getframerate()
            pcm = wav.readframes(wav.getnframes())
            return pcm, sample_rate
    except wave.Error:
        logger.debug("Fish-Speech response was not WAV; treating as raw PCM16.")
        return data, fallback_rate
