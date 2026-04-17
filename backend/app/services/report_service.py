from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language import Language
from app.models.session import Session
from app.models.user import User, UserLanguage


async def user_registration_report(
    db: AsyncSession, from_date: datetime, to_date: datetime
) -> dict:
    total_result = await db.execute(
        select(func.count(User.id)).where(
            User.created_at >= from_date,
            User.created_at <= to_date,
            User.deleted_at.is_(None),
        )
    )
    total = total_result.scalar() or 0

    daily_result = await db.execute(
        select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(
            User.created_at >= from_date,
            User.created_at <= to_date,
            User.deleted_at.is_(None),
        )
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    daily = [
        {"date": str(row.date), "count": row.count}
        for row in daily_result.all()
    ]

    return {"total_registrations": total, "daily": daily}


async def active_users_report(
    db: AsyncSession, from_date: datetime, to_date: datetime
) -> dict:
    active_result = await db.execute(
        select(func.count(func.distinct(Session.user_id))).where(
            Session.started_at >= from_date,
            Session.started_at <= to_date,
        )
    )
    active_users = active_result.scalar() or 0

    daily_result = await db.execute(
        select(
            func.date(Session.started_at).label("date"),
            func.count(func.distinct(Session.user_id)).label("count"),
        )
        .where(
            Session.started_at >= from_date,
            Session.started_at <= to_date,
        )
        .group_by(func.date(Session.started_at))
        .order_by(func.date(Session.started_at))
    )
    daily = [
        {"date": str(row.date), "count": row.count}
        for row in daily_result.all()
    ]

    return {"active_users": active_users, "daily": daily}


async def engagement_report(db: AsyncSession) -> dict:
    total_sessions_result = await db.execute(
        select(func.count(Session.id))
    )
    total_sessions = total_sessions_result.scalar() or 0

    avg_duration_result = await db.execute(
        select(func.avg(Session.duration_seconds)).where(
            Session.duration_seconds > 0
        )
    )
    avg_duration = avg_duration_result.scalar() or 0.0

    by_type_result = await db.execute(
        select(
            Session.session_type,
            func.count(Session.id).label("count"),
        ).group_by(Session.session_type)
    )
    by_type = {row.session_type: row.count for row in by_type_result.all()}

    by_mode_result = await db.execute(
        select(
            Session.session_mode,
            func.count(Session.id).label("count"),
        ).group_by(Session.session_mode)
    )
    by_mode = {row.session_mode: row.count for row in by_mode_result.all()}

    return {
        "total_sessions": total_sessions,
        "avg_duration_seconds": round(float(avg_duration), 2),
        "by_type": by_type,
        "by_mode": by_mode,
    }


async def language_analytics(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(
            Language.id,
            Language.name,
            Language.locale,
            func.count(UserLanguage.id).label("learner_count"),
        )
        .outerjoin(UserLanguage, Language.id == UserLanguage.language_id)
        .where(Language.deleted_at.is_(None))
        .group_by(Language.id, Language.name, Language.locale)
        .order_by(func.count(UserLanguage.id).desc())
    )
    return [
        {
            "language_id": str(row.id),
            "name": row.name,
            "locale": row.locale,
            "learner_count": row.learner_count,
        }
        for row in result.all()
    ]


# Aliases for route compatibility
get_registration_report = user_registration_report
get_active_users_report = active_users_report
get_engagement_report = engagement_report
get_language_analytics = language_analytics
