"""LiveKit Agents worker entrypoint for LangTutor."""

from __future__ import annotations

import json
import logging
from pathlib import Path

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
    proc.userdata["tts"] = FishSpeechTTS(
        base_url=settings.tts_base_url,
    )
    proc.userdata["avatar_enabled"] = settings.avatar_enabled
    proc.userdata["avatar_base_url"] = settings.avatar_base_url


async def _resolve_idle_video_path(session_id: str) -> Path | None:
    """Ask the internal API for the persona's idle-video path."""
    import httpx

    url = f"http://localhost:8000/api/internal/session-context/{session_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception:  # noqa: BLE001
        return None

    idle_url = data.get("persona_idle_video_url")
    if not idle_url:
        return None

    # idle_video_url is a relative path like /uploads/idle_loops/<id>.mp4
    path = Path(settings.upload_dir).parent / idle_url.lstrip("/")
    return path if path.exists() else None


async def _setup_avatar(ctx: JobContext, metadata: dict) -> None:
    """Spin up the avatar publisher if enabled. No-op otherwise."""
    if not ctx.proc.userdata.get("avatar_enabled"):
        return

    from app.ai.avatar_publisher import AvatarPublisher

    session_id = metadata.get("session_id", "")
    avatar_base_url: str = ctx.proc.userdata.get("avatar_base_url", settings.avatar_base_url)

    idle_video_path = await _resolve_idle_video_path(session_id)
    logger.info("avatar idle video: %s", idle_video_path)

    # Resolve the source path for lip-sync — same idle-loop MP4 the avatar
    # service has access to via its preload volume.  When the backend and
    # avatar service share a filesystem (same host), the paths match.
    # When they don't, the PRELOAD_DIR env in the avatar container should
    # contain the same file.
    source_path_for_avatar = str(idle_video_path) if idle_video_path else ""

    publisher = AvatarPublisher(
        room=ctx.room,
        avatar_ws_url=avatar_base_url,
        idle_video_path=idle_video_path,
    )
    await publisher.start()
    ctx.proc.userdata["_avatar_publisher"] = publisher

    # Wire TTS audio listener so every synthesised utterance is sent to
    # the avatar service for real-time lip-sync.
    tts_plugin: FishSpeechTTS = ctx.proc.userdata["tts"]

    async def _on_tts_audio(audio_wav: bytes) -> None:
        if source_path_for_avatar:
            await publisher.render_speech(audio_wav, source_path_for_avatar)

    tts_plugin.add_audio_listener(_on_tts_audio)

    # Clean up on disconnect.
    @ctx.room.on("disconnected")
    def _on_disconnect() -> None:
        import asyncio
        asyncio.ensure_future(publisher.stop())


async def entrypoint(ctx: JobContext) -> None:
    """Main entrypoint for the LiveKit Agents worker.

    Connects to the room, determines the agent type from room metadata,
    creates the appropriate agent, and starts it with a greeting.
    """
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    room = ctx.room
    metadata = json.loads(room.metadata or "{}")
    agent_type = metadata.get("agent_type", "tutor")

    logger.info(
        "Starting agent: type=%s, room=%s", agent_type, room.name,
    )

    # Start avatar publisher before the assistant so video is ready
    # by the time the greeting plays.
    if agent_type not in ("onboarding", "support"):
        await _setup_avatar(ctx, metadata)

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


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
