"""Gemini LLM plugin for LiveKit Agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterable

import google.generativeai as genai
from livekit.agents import llm

from app.config import settings


@dataclass
class ChatChunk:
    """A single chunk of streamed chat output."""

    text: str
    is_final: bool = True


class GeminiChatStream:
    """Wraps a Gemini response to yield ChatChunk objects."""

    def __init__(self, response_text: str) -> None:
        self._text = response_text
        self._consumed = False

    def __aiter__(self) -> GeminiChatStream:
        return self

    async def __anext__(self) -> ChatChunk:
        if self._consumed:
            raise StopAsyncIteration
        self._consumed = True
        return ChatChunk(text=self._text, is_final=True)


class GeminiLLM(llm.LLM):
    """LiveKit Agents LLM implementation backed by Google Gemini."""

    def __init__(self) -> None:
        super().__init__()
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel("gemini-1.5-flash")
        self._chat = None

    def _convert_messages(
        self, messages: list[llm.ChatMessage],
    ) -> list[dict]:
        """Convert LiveKit ChatMessage objects to Gemini message format."""
        gemini_messages: list[dict] = []
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            gemini_messages.append({
                "role": role,
                "parts": [msg.content],
            })
        return gemini_messages

    async def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        **kwargs,
    ) -> GeminiChatStream:
        """Send a chat message to Gemini and return a streaming response."""
        messages = self._convert_messages(chat_ctx.messages)

        # Separate system instruction from conversation history
        system_parts: list[str] = []
        history: list[dict] = []
        for m in messages:
            if m["role"] == "model" and not history:
                # Treat leading model messages as system context
                system_parts.append(m["parts"][0])
            else:
                history.append(m)

        # Start a new chat with history (excluding the last user message)
        chat_history = history[:-1] if history else []
        last_message = history[-1]["parts"][0] if history else ""

        self._chat = self._model.start_chat(history=chat_history)
        response = await self._chat.send_message_async(last_message)

        return GeminiChatStream(response.text)
