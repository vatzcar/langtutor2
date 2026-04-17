import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    price_yearly: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    text_learning_limit_minutes: Mapped[int] = mapped_column(Integer, default=0)
    voice_call_limit_minutes: Mapped[int] = mapped_column(Integer, default=0)
    video_call_limit_minutes: Mapped[int] = mapped_column(Integer, default=0)
    agentic_voice_limit_monthly: Mapped[int] = mapped_column(Integer, default=0)
    coordinator_video_limit_monthly: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
