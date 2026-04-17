from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


async def list_support_sessions(db: AsyncSession, user_id: UUID) -> list[dict]:
    result = await db.execute(
        select(Session)
        .where(
            Session.user_id == user_id,
            Session.session_type == "coordinator",
        )
        .order_by(Session.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "session_type": s.session_type,
            "session_mode": s.session_mode,
            "created_at": s.created_at.isoformat(),
            "duration_seconds": s.duration_seconds,
        }
        for s in sessions
    ]
