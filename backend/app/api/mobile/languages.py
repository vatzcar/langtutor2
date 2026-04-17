from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserLanguage
from app.schemas.language import LanguageResponse
from app.schemas.user import UserLanguageResponse
from app.services import language as language_service

router = APIRouter(prefix="/mobile/languages", tags=["mobile-languages"])


@router.get("", response_model=list[LanguageResponse])
async def list_active_languages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await language_service.list_languages(db, include_inactive=False)
