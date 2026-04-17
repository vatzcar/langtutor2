from uuid import UUID

from pydantic import BaseModel


class PlanUpdate(BaseModel):
    price_monthly: float | None = None
    price_yearly: float | None = None
    text_learning_limit_minutes: int | None = None
    voice_call_limit_minutes: int | None = None
    video_call_limit_minutes: int | None = None
    agentic_voice_limit_monthly: int | None = None
    coordinator_video_limit_monthly: int | None = None


class PlanResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    slug: str
    price_monthly: float
    price_yearly: float
    text_learning_limit_minutes: int
    voice_call_limit_minutes: int
    video_call_limit_minutes: int
    agentic_voice_limit_monthly: int
    coordinator_video_limit_monthly: int
    is_active: bool
