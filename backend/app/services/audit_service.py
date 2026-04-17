from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    actor_type: str,
    actor_id: UUID,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(log)
    await db.flush()
    return log


async def get_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    actor_type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> list[AuditLog]:
    stmt = select(AuditLog)

    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if actor_type is not None:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if from_date is not None:
        stmt = stmt.where(AuditLog.created_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(AuditLog.created_at <= to_date)

    sort_column = getattr(AuditLog, sort_by, AuditLog.created_at)
    if sort_order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
