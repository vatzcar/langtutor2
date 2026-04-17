from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.subscription import UserSubscription
from app.models.usage import DailyUsage


async def get_daily_usage(
    db: AsyncSession, user_id: UUID, usage_date: date | None = None
) -> DailyUsage:
    if usage_date is None:
        usage_date = datetime.now(timezone.utc).date()

    result = await db.execute(
        select(DailyUsage).where(
            DailyUsage.user_id == user_id, DailyUsage.date == usage_date
        )
    )
    usage = result.scalar_one_or_none()

    if usage is None:
        usage = DailyUsage(
            user_id=user_id,
            date=usage_date,
        )
        db.add(usage)
        await db.flush()

    return usage


async def check_limit(
    db: AsyncSession, user_id: UUID, feature: str
) -> dict:
    # Get active subscription and plan limits
    sub_result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_active.is_(True),
        )
    )
    subscription = sub_result.scalar_one_or_none()

    if subscription is None:
        return {"allowed": False, "remaining_minutes": 0.0}

    plan_result = await db.execute(
        select(Plan).where(Plan.id == subscription.plan_id)
    )
    plan = plan_result.scalar_one_or_none()

    if plan is None:
        return {"allowed": False, "remaining_minutes": 0.0}

    # Map feature to plan limit and usage field
    feature_map = {
        "voice_call": ("voice_call_limit_minutes", "voice_call_minutes"),
        "video_call": ("video_call_limit_minutes", "video_call_minutes"),
        "text_learning": ("text_learning_limit_minutes", "text_learning_minutes"),
    }

    if feature not in feature_map:
        return {"allowed": False, "remaining_minutes": 0.0}

    limit_field, usage_field = feature_map[feature]
    daily_limit = getattr(plan, limit_field, 0)

    # -1 = Not Available for this plan
    if daily_limit == -1:
        return {"allowed": False, "remaining_minutes": 0.0, "unlimited": False}

    # 0 = Unlimited
    if daily_limit == 0:
        return {"allowed": True, "remaining_minutes": 0.0, "unlimited": True}

    # Positive = specific minute limit
    usage = await get_daily_usage(db, user_id)
    used = getattr(usage, usage_field, 0.0)
    remaining = max(0.0, daily_limit - used)

    return {"allowed": remaining > 0, "remaining_minutes": remaining, "unlimited": False}


async def record_usage(
    db: AsyncSession, user_id: UUID, feature: str, minutes: float
) -> None:
    usage = await get_daily_usage(db, user_id)

    feature_field_map = {
        "voice_call": "voice_call_minutes",
        "video_call": "video_call_minutes",
        "text_learning": "text_learning_minutes",
    }

    field = feature_field_map.get(feature)
    if field is None:
        raise ValueError(f"Unknown feature: {feature}")

    current = getattr(usage, field, 0.0)
    setattr(usage, field, current + minutes)
    await db.flush()
