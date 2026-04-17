from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permission
from app.models.admin import AdminUser
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
)
from app.services import admin_user as admin_user_service

router = APIRouter(prefix="/admin/admin-users", tags=["admin-admin-users"])


@router.get("", response_model=list[AdminUserResponse])
async def list_admin_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.view")),
):
    return await admin_user_service.list_admin_users(
        db, skip=skip, limit=limit
    )


@router.get("/{admin_id}", response_model=AdminUserResponse)
async def get_admin_user(
    admin_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.view")),
):
    target = await admin_user_service.get_admin_user(db, admin_id)
    if not target:
        raise HTTPException(status_code=404, detail="Admin user not found")
    return target


@router.post("", response_model=AdminUserResponse)
async def create_admin_user(
    body: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.add")),
):
    return await admin_user_service.create_admin_user(db, body)


@router.patch("/{admin_id}", response_model=AdminUserResponse)
async def update_admin_user(
    admin_id: UUID,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.edit")),
):
    try:
        target = await admin_user_service.update_admin_user(db, admin_id, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not target:
        raise HTTPException(status_code=404, detail="Admin user not found")
    return target


@router.post("/{admin_id}/toggle-active", response_model=AdminUserResponse)
async def toggle_admin_active(
    admin_id: UUID,
    is_active: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.edit")),
):
    try:
        target = await admin_user_service.toggle_admin_active(
            db, admin_id, is_active
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not target:
        raise HTTPException(status_code=404, detail="Admin user not found")
    return target


@router.delete("/{admin_id}", status_code=204)
async def delete_admin_user(
    admin_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.delete")),
):
    try:
        deleted = await admin_user_service.delete_admin_user(db, admin_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Admin user not found")
