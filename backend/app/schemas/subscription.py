from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SubscriptionCreate(BaseModel):
    plan_id: UUID
    billing_cycle: str = "monthly"
    store_transaction_id: str | None = None
    store_type: str | None = None


class SubscriptionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    user_id: UUID
    plan_id: UUID
    billing_cycle: str
    started_at: datetime
    expires_at: datetime | None
    is_active: bool
