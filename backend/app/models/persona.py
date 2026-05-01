import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.language import Language


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class PersonaType(str, enum.Enum):
    teacher = "teacher"
    coordinator = "coordinator"
    peer = "peer"


class TeachingStyle(str, enum.Enum):
    casual_friendly = "casual_friendly"
    friendly_structured = "friendly_structured"
    formal_structured = "formal_structured"


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    language_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("languages.id"))
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    idle_video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gender: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(20))
    teaching_style: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    language: Mapped[Language] = relationship(lazy="joined")
