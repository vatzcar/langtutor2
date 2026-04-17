"""Tutor and practice agent factory for LiveKit Agents."""

from __future__ import annotations

import json
import logging

import httpx
from livekit.agents import JobContext
from livekit.agents.voice_assistant import VoiceAssistant

from app.ai.cefr_assessor import get_reinforcement_topics, get_topics_for_level
from app.ai.gemini_plugin import GeminiLLM
from app.ai.prompt_templates import (
    PRACTICE_SYSTEM_PROMPT,
    TUTOR_SYSTEM_PROMPT,
    get_native_language_rule,
)

logger = logging.getLogger(__name__)

INTERNAL_API_BASE = "http://localhost:8000/api/internal"


async def fetch_user_context(session_id: str) -> dict:
    """Fetch user/session context from the backend's internal API."""
    url = f"{INTERNAL_API_BASE}/session-context/{session_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


def create_tutor_agent(ctx: JobContext) -> VoiceAssistant:
    """Create a tutor or practice VoiceAssistant based on room metadata."""
    room = ctx.room
    metadata = json.loads(room.metadata or "{}")

    session_id = metadata.get("session_id", "")
    mode = metadata.get("mode", "tutor")  # "tutor" or "practice"

    # Fetch context synchronously-style — this runs before the agent starts
    import asyncio

    context = asyncio.get_event_loop().run_until_complete(
        fetch_user_context(session_id)
    )

    target_language = context.get("target_language", "English")
    native_language = context.get("native_language", "English")
    student_name = context.get("student_name", "Student")
    cefr_level = context.get("cefr_level", "A0")
    progress_percent = context.get("progress_percent", 0)
    teaching_style = context.get("teaching_style", "balanced")
    topics_covered = context.get("topics_covered", [])
    weaknesses = context.get("weaknesses", [])

    if mode == "practice":
        system_prompt = PRACTICE_SYSTEM_PROMPT.format(
            target_language=target_language,
            student_name=student_name,
            cefr_level=cefr_level,
            topics_covered=", ".join(topics_covered) if topics_covered else "none yet",
        )
    else:
        # Tutor mode — include reinforcement topics
        all_topics = get_topics_for_level(cefr_level)
        reinforcement = get_reinforcement_topics(cefr_level)
        use_native_language_rule = get_native_language_rule(cefr_level)

        system_prompt = TUTOR_SYSTEM_PROMPT.format(
            target_language=target_language,
            native_language=native_language,
            student_name=student_name,
            cefr_level=cefr_level,
            progress_percent=progress_percent,
            teaching_style=teaching_style,
            topics_covered=", ".join(topics_covered) if topics_covered else "none yet",
            weaknesses=", ".join(weaknesses) if weaknesses else "none identified",
            use_native_language_rule=use_native_language_rule,
        )

    llm = GeminiLLM()

    assistant = VoiceAssistant(
        vad=ctx.proc.userdata.get("vad"),
        stt=ctx.proc.userdata.get("stt"),
        llm=llm,
        tts=ctx.proc.userdata.get("tts"),
        chat_ctx=llm.ChatContext().append(role="system", text=system_prompt),
    )

    return assistant
