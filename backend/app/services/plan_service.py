from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.schemas.plan import PlanUpdate


async def get_plans(db: AsyncSession) -> list[Plan]:
    result = await db.execute(
        select(Plan)
        .where(Plan.is_active.is_(True))
        .order_by(Plan.price_monthly)
    )
    return list(result.scalars().all())


list_plans = get_plans


async def get_plan(db: AsyncSession, plan_id: UUID) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    return result.scalar_one_or_none()


async def get_plan_by_slug(db: AsyncSession, slug: str) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.slug == slug))
    return result.scalar_one_or_none()


async def update_plan(
    db: AsyncSession, plan_id: UUID, data: PlanUpdate
) -> Plan | None:
    plan = await get_plan(db, plan_id)
    if plan is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plan, key, value)

    await db.flush()
    return plan
