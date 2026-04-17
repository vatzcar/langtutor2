from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.subscription import UserSubscription


async def get_active_subscription(
    db: AsyncSession, user_id: UUID
) -> UserSubscription | None:
    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def create_subscription(
    db: AsyncSession,
    user_id: UUID,
    plan_id: UUID,
    billing_cycle: str,
    store_transaction_id: str | None = None,
    store_type: str | None = None,
) -> UserSubscription:
    # Deactivate existing active subscriptions
    await db.execute(
        update(UserSubscription)
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_active.is_(True),
        )
        .values(is_active=False)
    )

    now = datetime.now(timezone.utc)
    if billing_cycle == "yearly":
        expires_at = now + timedelta(days=365)
    else:
        expires_at = now + timedelta(days=30)

    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan_id,
        billing_cycle=billing_cycle,
        started_at=now,
        expires_at=expires_at,
        store_transaction_id=store_transaction_id,
        store_type=store_type,
        is_active=True,
    )
    db.add(subscription)
    await db.flush()
    return subscription


async def change_subscription(
    db: AsyncSession,
    user_id: UUID,
    new_plan_id: UUID,
    new_billing_cycle: str,
) -> dict:
    old_sub = await get_active_subscription(db, user_id)

    credit_days = 0
    if old_sub is not None and old_sub.expires_at is not None:
        now = datetime.now(timezone.utc)
        remaining = old_sub.expires_at - now
        credit_days = max(0, remaining.days)

        # Fetch old plan price for pro-rata calculation
        old_plan_result = await db.execute(
            select(Plan).where(Plan.id == old_sub.plan_id)
        )
        old_plan = old_plan_result.scalar_one_or_none()

        old_price = float(
            old_plan.price_yearly if old_sub.billing_cycle == "yearly" else old_plan.price_monthly
        ) if old_plan else 0.0
        total_days = 365 if old_sub.billing_cycle == "yearly" else 30
        credit_amount = (old_price / total_days) * credit_days if total_days > 0 else 0.0
    else:
        credit_amount = 0.0

    new_sub = await create_subscription(
        db, user_id, new_plan_id, new_billing_cycle
    )

    return {
        "old_subscription_id": str(old_sub.id) if old_sub else None,
        "new_subscription_id": str(new_sub.id),
        "credit_days": credit_days,
        "credit_amount": round(credit_amount, 2),
    }
