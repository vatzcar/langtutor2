from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services import support as support_service

router = APIRouter(prefix="/mobile/support", tags=["mobile-support"])


@router.get("/history")
async def list_support_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await support_service.list_support_sessions(db, current_user.id)
