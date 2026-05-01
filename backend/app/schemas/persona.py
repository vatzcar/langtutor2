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
    image_url: str | None = None
    is_active: bool | None = None


class PersonaResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    language_id: UUID
    image_url: str | None
    idle_video_url: str | None = None
    gender: str
    type: str
    teaching_style: str | None
    is_active: bool
    created_at: datetime


class PersonaWithStatusResponse(PersonaResponse):
    idle_loop_status: str = "none"

    @classmethod
    def from_persona(cls, persona: "PersonaResponse") -> "PersonaWithStatusResponse":
        data = persona.model_dump()
        if data.get("idle_video_url"):
            data["idle_loop_status"] = "ready"
        elif data.get("image_url"):
            data["idle_loop_status"] = "pending"
        else:
            data["idle_loop_status"] = "none"
        return cls(**data)
