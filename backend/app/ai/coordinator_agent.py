"""Coordinator (onboarding/support) agent factory for LiveKit Agents."""

from __future__ import annotations

import json
import logging

from livekit.agents import JobContext
from livekit.agents.voice_assistant import VoiceAssistant

from app.ai.gemini_plugin import GeminiLLM
from app.ai.prompt_templates import COORDINATOR_SYSTEM_PROMPT, SUPPORT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def create_coordinator_agent(ctx: JobContext) -> VoiceAssistant:
    """Create a coordinator or support VoiceAssistant based on room metadata."""
    room = ctx.room
    metadata = json.loads(room.metadata or "{}")

    mode = metadata.get("mode", "onboarding")  # "onboarding" or "support"

    if mode == "support":
        student_name = metadata.get("student_name", "there")
        plan_name = metadata.get("plan_name", "Free")
        languages = metadata.get("languages", [])

        system_prompt = SUPPORT_SYSTEM_PROMPT.format(
            student_name=student_name,
            plan_name=plan_name,
            languages=", ".join(languages) if languages else "none yet",
        )
    else:
        # Onboarding mode
        native_language = metadata.get("native_language", "English")
        locale = metadata.get("locale", "en-US")
        available_languages = metadata.get(
            "available_languages",
            "English, Spanish, French, German, Japanese, Korean, "
            "Mandarin Chinese, Portuguese, Italian, Arabic",
        )
        fallback_language = metadata.get("fallback_language", "English")

        system_prompt = COORDINATOR_SYSTEM_PROMPT.format(
            native_language=native_language,
            locale=locale,
            available_languages=available_languages,
            fallback_language=fallback_language,
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
