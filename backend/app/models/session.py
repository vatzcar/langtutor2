import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SessionType(str, enum.Enum):
    voice_call = "voice_call"
    video_call = "video_call"
    text_chat = "text_chat"


class SessionMode(str, enum.Enum):
    learning = "learning"
    practice = "practice"
    support = "support"
    onboarding = "onboarding"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    user_language_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_languages.id"), nullable=True
    )
    persona_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personas.id"))
    session_type: Mapped[str] = mapped_column(String(20))
    session_mode: Mapped[str] = mapped_column(String(20))
    livekit_room_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    cefr_level_at_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    topics_covered: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    performance_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    skills_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    vocabulary_tracked: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class SessionTranscript(Base):
    __tablename__ = "session_transcripts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    speaker: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    timestamp_offset_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    sender: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
