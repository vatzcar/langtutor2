from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    name: str
    auth_provider: str
    auth_provider_id: str


class UserUpdate(BaseModel):
    name: str | None = None
    date_of_birth: date | None = None
    native_language_id: UUID | None = None
    avatar_id: UUID | None = None


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    email: str
    name: str
    date_of_birth: date | None
    avatar_id: UUID | None
    native_language_id: UUID | None
    is_active: bool
    is_banned: bool
    created_at: datetime


class UserLanguageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    language_id: UUID
    teacher_persona_id: UUID | None
    teaching_style: str | None
    current_cefr_level: str
    cefr_progress_percent: float
    is_active: bool
