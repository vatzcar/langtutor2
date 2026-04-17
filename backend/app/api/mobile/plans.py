from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.plan import PlanResponse
from app.services import plan as plan_service

router = APIRouter(prefix="/mobile/plans", tags=["mobile-plans"])


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await plan_service.list_plans(db)
