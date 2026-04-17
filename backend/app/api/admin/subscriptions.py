from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permission
from app.models.admin import AdminUser
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse
from app.services import subscription as subscription_service

router = APIRouter(prefix="/admin/subscriptions", tags=["admin-subscriptions"])


class ExpiryUpdate(BaseModel):
    expires_at: datetime | None = None


@router.get("/user/{user_id}", response_model=SubscriptionResponse)
async def get_user_subscription(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.view")),
):
    sub = await subscription_service.get_active_subscription(db, user_id)
    if not sub:
        raise HTTPException(
            status_code=404, detail="No active subscription for user"
        )
    return sub


@router.post("/user/{user_id}/assign", response_model=SubscriptionResponse)
async def assign_user_subscription(
    user_id: UUID,
    body: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.edit")),
):
    sub = await subscription_service.create_subscription(
        db,
        user_id=user_id,
        plan_id=body.plan_id,
        billing_cycle=body.billing_cycle,
        store_transaction_id=body.store_transaction_id,
        store_type=body.store_type,
    )
    return sub


@router.patch("/user/{user_id}/expiry", response_model=SubscriptionResponse)
async def update_user_subscription_expiry(
    user_id: UUID,
    body: ExpiryUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("users.edit")),
):
    sub = await subscription_service.get_active_subscription(db, user_id)
    if not sub:
        raise HTTPException(
            status_code=404, detail="No active subscription for user"
        )
    sub.expires_at = body.expires_at
    await db.flush()
    return sub
