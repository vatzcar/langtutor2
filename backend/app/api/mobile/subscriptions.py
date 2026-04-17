from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse
from app.services import subscription as subscription_service

router = APIRouter(prefix="/mobile/subscriptions", tags=["mobile-subscriptions"])


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = await subscription_service.get_active_subscription(db, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    return sub


@router.post("", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.create_subscription(db, current_user.id, body)


@router.post("/change", response_model=SubscriptionResponse)
async def change_subscription(
    body: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await subscription_service.change_subscription(db, current_user.id, body)
