from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserBan
from app.schemas.user import UserUpdate


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
) -> list[User]:
    stmt = select(User).where(User.deleted_at.is_(None))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(User.name.ilike(pattern), User.email.ilike(pattern))
        )
    stmt = stmt.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


list_users = get_users


async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession, user_id: UUID, data: UserUpdate
) -> User | None:
    user = await get_user(db, user_id)
    if user is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await db.flush()
    return user


async def toggle_user_active(
    db: AsyncSession, user_id: UUID, is_active: bool
) -> User | None:
    user = await get_user(db, user_id)
    if user is None:
        return None

    user.is_active = is_active
    await db.flush()
    return user


toggle_active = toggle_user_active


async def soft_delete_user(db: AsyncSession, user_id: UUID) -> bool:
    user = await get_user(db, user_id)
    if user is None:
        return False

    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    await db.flush()
    return True


delete_user = soft_delete_user


async def ban_user(
    db: AsyncSession,
    user_id: UUID,
    reason: str,
    expires_at: datetime | None = None,
) -> UserBan:
    user = await get_user(db, user_id)
    if user is None:
        raise ValueError("User not found")

    user.is_banned = True
    user.ban_expires_at = expires_at

    ban = UserBan(
        user_id=user_id,
        reason=reason,
        expires_at=expires_at,
    )
    db.add(ban)
    await db.flush()
    return ban


async def unban_user(db: AsyncSession, user_id: UUID) -> User | None:
    user = await get_user(db, user_id)
    if user is None:
        return None

    user.is_banned = False
    user.ban_expires_at = None

    result = await db.execute(
        select(UserBan)
        .where(UserBan.user_id == user_id, UserBan.unbanned_at.is_(None))
        .order_by(UserBan.created_at.desc())
        .limit(1)
    )
    latest_ban = result.scalar_one_or_none()
    if latest_ban is not None:
        latest_ban.unbanned_at = datetime.now(timezone.utc)

    await db.flush()
    return user
