from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permission
from app.models.admin import AdminUser
from app.schemas.admin import AdminRoleCreate, AdminRoleResponse
from app.services import admin_role as admin_role_service

router = APIRouter(prefix="/admin/roles", tags=["admin-roles"])


@router.get("", response_model=list[AdminRoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.view")),
):
    return await admin_role_service.list_roles(db)


@router.post("", response_model=AdminRoleResponse)
async def create_role(
    body: AdminRoleCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.add")),
):
    return await admin_role_service.create_role(db, body)


@router.get("/{role_id}", response_model=AdminRoleResponse)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.view")),
):
    role = await admin_role_service.get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.put("/{role_id}", response_model=AdminRoleResponse)
async def update_role(
    role_id: UUID,
    body: AdminRoleCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.edit")),
):
    try:
        role = await admin_role_service.update_role(db, role_id, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("admins.delete")),
):
    try:
        deleted = await admin_role_service.delete_role(db, role_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Role not found")
