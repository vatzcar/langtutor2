from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permission
from app.models.admin import AdminUser
from app.schemas.plan import PlanUpdate, PlanResponse
from app.services import plan as plan_service

router = APIRouter(prefix="/admin/plans", tags=["admin-plans"])


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("plans.manage")),
):
    return await plan_service.list_plans(db)


@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: UUID,
    body: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("plans.manage")),
):
    plan = await plan_service.update_plan(db, plan_id, body)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan
