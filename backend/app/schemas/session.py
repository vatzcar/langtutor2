from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SessionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    session_type: str
    session_mode: str
    duration_seconds: int
    cefr_level_at_time: str | None
    started_at: datetime
    ended_at: datetime | None


class TranscriptResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    speaker: str
    content: str
    timestamp_offset_ms: int
    created_at: datetime


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    sender: str
    content: str
    is_read: bool
    created_at: datetime
