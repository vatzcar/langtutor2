from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PersonaCreate(BaseModel):
    name: str
    language_id: UUID
    gender: str
    type: str
    teaching_style: str | None = None


class PersonaUpdate(BaseModel):
    name: str | None = None
    gender: str | None = None
    type: str | None = None
    teaching_style: str | None = None
    is_active: bool | None = None


class PersonaResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    language_id: UUID
    image_url: str | None
    gender: str
    type: str
    teaching_style: str | None
    is_active: bool
    created_at: datetime
