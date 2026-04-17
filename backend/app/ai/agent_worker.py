"""LiveKit Agents worker entrypoint for LangTutor."""

from __future__ import annotations

import json
import logging

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
