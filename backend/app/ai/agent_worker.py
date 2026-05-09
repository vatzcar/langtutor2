"""LiveKit Agents worker entrypoint for LangTutor."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from livekit.agents import AutoSubscribe, JobContext, JobProcess, WorkerOptions, cli
from livekit.plugins import silero

from app.ai.coordinator_agent import create_coordinator_agent
from app.ai.stt_plugin import FasterWhisperSTT
from app.ai.tts_plugin import FishSpeechTTS
from app.ai.tutor_agent import create_tutor_agent
from app.config import settings

logger = logging.getLogger(__name__)


def prewarm(proc: JobProcess) -> None:
    """Prewarm function — runs once per worker process.

    Loads the silero VAD (CPU-only, ~40 MB) and instantiates the STT and
    TTS plugin clients. These objects are stashed in ``proc.userdata`` so
    each job can reuse them (saves model reload + HTTP connection setup
    per call).
    """
    logger.info("Prewarming worker process: loading VAD + STT/TTS clients.")
    proc.userdata["vad"] = silero.VAD.load()
    proc.userdata["stt"] = FasterWhisperSTT(
        base_url=settings.stt_base_url,
        model=settings.stt_model,
    )
    proc.userdata["avatar_enabled"] = settings.avatar_enabled
    proc.userdata["avatar_base_url"] = settings.avatar_base_url


async def entrypoint(ctx: JobContext) -> None:
    """Main entrypoint for the LiveKit Agents worker.

    Connects to the room, determines the agent type from room metadata,
    creates the appropriate agent, and starts it with a greeting.
    """
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    room = ctx.room
    metadata = json.loads(room.metadata or "{}")
    agent_type = metadata.get("agent_type", "tutor")
    avatar_enabled = ctx.proc.userdata.get("avatar_enabled", False)

    logger.info(
        "Starting agent: type=%s, room=%s, avatar=%s",
        agent_type, room.name, avatar_enabled,
    )

    # Set up avatar publisher if enabled (tutor sessions only)
    publisher: Optional["AvatarPublisher"] = None  # noqa: F821
    tts_on_audio = None

    if avatar_enabled and agent_type not in ("onboarding", "support"):
        try:
            from app.ai.avatar_publisher import AvatarPublisher

            avatar_base_url = ctx.proc.userdata.get(
                "avatar_base_url", settings.avatar_base_url,
            )
            ws_url = avatar_base_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = f"{ws_url}/stream"

            idle_video_path = _resolve_idle_video(metadata)

            publisher = AvatarPublisher(
                room=room,
                avatar_ws_url=ws_url,
                idle_video_path=idle_video_path,
            )
            await publisher.start()

            async def _on_tts_audio(audio_bytes: bytes) -> None:
                if publisher is not None:
                    await publisher.send_audio(audio_bytes)

            tts_on_audio = _on_tts_audio
            logger.info("avatar publisher started for room %s", room.name)
        except Exception:  # noqa: BLE001
            logger.exception("failed to start avatar publisher — continuing without avatar")
            publisher = None

    tts = FishSpeechTTS(
        base_url=settings.tts_base_url,
        on_audio=tts_on_audio,
    )
    ctx.proc.userdata["tts"] = tts

    if agent_type in ("onboarding", "support"):
        assistant = create_coordinator_agent(ctx)
        if agent_type == "onboarding":
            greeting = "Hello! Welcome to LangTutor. I'm here to help you get started."
        else:
            greeting = "Hi there! I'm the LangTutor support assistant. How can I help you today?"
    else:
        assistant = create_tutor_agent(ctx)
        mode = metadata.get("mode", "tutor")
        student_name = metadata.get("student_name", "there")
        if mode == "practice":
            greeting = f"Hey {student_name}! Ready to practice? Let's have a conversation."
        else:
            greeting = f"Hello {student_name}! Great to see you. Let's continue your lesson."

    assistant.start(ctx.room)
    await assistant.say(greeting)

    # Keep alive until the session ends — clean up avatar publisher on disconnect
    @room.on("disconnected")
    async def _on_disconnect():
        if publisher is not None:
            await publisher.stop()
        await tts.aclose()


def _resolve_idle_video(metadata: dict) -> Optional[Path]:
    """Find the persona's pre-rendered idle-loop MP4, if any."""
    persona_id = metadata.get("persona_id")
    if not persona_id:
        return None
    candidate = Path(settings.upload_dir) / "idle_loops" / f"{persona_id}.mp4"
    if candidate.exists():
        return candidate
    return None


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
