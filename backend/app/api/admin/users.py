from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permission
from app.models.admin import AdminUser
from app.schemas.user import UserUpdate, UserResponse
from app.services import user as user_service

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class BanRequest(BaseModel):
    reason: str
    expires_at: datetime | None = None


@router.get("", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.view")),
):
    return await user_service.list_users(db, skip=skip, limit=limit, search=search)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.view")),
):
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.edit")),
):
    user = await user_service.update_user(db, user_id, body)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(
    user_id: UUID,
    is_active: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.edit")),
):
    user = await user_service.toggle_active(db, user_id, is_active)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.delete")),
):
    deleted = await user_service.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/{user_id}/ban", response_model=UserResponse)
async def ban_user(
    user_id: UUID,
    body: BanRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.edit")),
):
    try:
        await user_service.ban_user(db, user_id, body.reason, body.expires_at)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")
    user = await user_service.get_user(db, user_id)
    return user


@router.post("/{user_id}/unban", response_model=UserResponse)
async def unban_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.edit")),
):
    user = await user_service.unban_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
