from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import AdminUser
from app.schemas.auth import SocialLoginRequest, AdminLoginRequest, TokenResponse
from app.services.auth_service import social_login as do_social_login, admin_login as do_admin_login

router = APIRouter(prefix="/auth", tags=["auth"])


class AdminMeRoleResponse(BaseModel):
    id: UUID
    name: str
    permissions: list[str]


class AdminMeResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: AdminMeRoleResponse


@router.post("/social-login", response_model=TokenResponse)
async def social_login(body: SocialLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, token, is_new = await do_social_login(db, body.provider, body.id_token)
        return TokenResponse(access_token=token, user_id=str(user.id))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(body: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        admin, token = await do_admin_login(db, body.email, body.password)
        return TokenResponse(access_token=token, user_id=str(admin.id))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=AdminMeResponse)
async def get_me(admin: AdminUser = Depends(get_current_admin)):
    return AdminMeResponse(
        id=admin.id,
        email=admin.email,
        name=admin.name,
        role=AdminMeRoleResponse(
            id=admin.role.id,
            name=admin.role.name,
            permissions=list(admin.role.permissions or []),
        ),
    )
