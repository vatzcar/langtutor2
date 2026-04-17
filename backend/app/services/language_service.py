from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language import Language
from app.schemas.language import LanguageCreate, LanguageUpdate


async def create_language(db: AsyncSession, data: LanguageCreate) -> Language:
    if data.is_fallback:
        await db.execute(
            update(Language)
            .where(Language.is_fallback.is_(True))
            .values(is_fallback=False)
        )

    language = Language(
        name=data.name,
        locale=data.locale,
        is_default=data.is_default,
        is_fallback=data.is_fallback,
        is_active=True,
    )
    db.add(language)
    await db.flush()
    return language


async def get_languages(
    db: AsyncSession, include_inactive: bool = False
) -> list[Language]:
    stmt = select(Language).where(Language.deleted_at.is_(None))
    if not include_inactive:
        stmt = stmt.where(Language.is_active.is_(True))
    stmt = stmt.order_by(Language.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_language(db: AsyncSession, language_id: UUID) -> Language | None:
    result = await db.execute(
        select(Language).where(
            Language.id == language_id, Language.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def update_language(
    db: AsyncSession, language_id: UUID, data: LanguageUpdate
) -> Language | None:
    language = await get_language(db, language_id)
    if language is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    if update_data.get("is_fallback") is True:
        await db.execute(
            update(Language)
            .where(Language.is_fallback.is_(True), Language.id != language_id)
            .values(is_fallback=False)
        )

    for key, value in update_data.items():
        setattr(language, key, value)

    await db.flush()
    return language


# Alias for route compatibility
list_languages = get_languages


async def delete_language(db: AsyncSession, language_id: UUID) -> bool:
    language = await get_language(db, language_id)
    if language is None:
        return False

    language.deleted_at = datetime.now(timezone.utc)
    language.is_active = False
    await db.flush()
    return True
