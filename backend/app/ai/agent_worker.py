"""LiveKit Agents worker entrypoint for LangTutor."""

from __future__ import annotations

import json
import logging

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli

from app.ai.coordinator_agent import create_coordinator_agent
from app.ai.tutor_agent import create_tutor_agent

logger = logging.getLogger(__name__)


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
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
