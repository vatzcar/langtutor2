from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminRoleCreate(BaseModel):
    name: str
    permissions: list[str]


class AdminRoleResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    permissions: list[str]
    created_at: datetime


class AdminUserCreate(BaseModel):
    email: str
    name: str
    password: str
    role_id: UUID


class AdminUserUpdate(BaseModel):
    name: str | None = None
    role_id: UUID | None = None
    is_active: bool | None = None


class AdminUserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    email: str
    name: str
    role_id: UUID
    is_active: bool
    created_at: datetime
