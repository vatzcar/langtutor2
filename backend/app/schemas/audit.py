from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    actor_type: str
    actor_id: UUID
    action: str
    resource_type: str | None
    resource_id: UUID | None
    details: dict | None
    ip_address: str | None
    created_at: datetime
