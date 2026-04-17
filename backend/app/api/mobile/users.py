from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserLanguage
from app.schemas.user import UserUpdate, UserResponse, UserLanguageResponse
from app.services import user as user_service

router = APIRouter(prefix="/mobile/users", tags=["mobile-users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await user_service.update_user(db, current_user.id, body)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me/languages", response_model=list[UserLanguageResponse])
async def get_my_languages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserLanguage)
        .where(UserLanguage.user_id == current_user.id, UserLanguage.is_active.is_(True))
        .order_by(UserLanguage.created_at)
    )
    return result.scalars().all()
