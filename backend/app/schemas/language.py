from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LanguageCreate(BaseModel):
    name: str
    locale: str
    is_default: bool = False
    is_fallback: bool = False


class LanguageUpdate(BaseModel):
    name: str | None = None
    locale: str | None = None
    is_default: bool | None = None
    is_fallback: bool | None = None
    is_active: bool | None = None


class LanguageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    locale: str
    icon_url: str | None
    is_default: bool
    is_fallback: bool
    is_active: bool
    created_at: datetime
