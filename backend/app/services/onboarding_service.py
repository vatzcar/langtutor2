from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language import Language
from app.models.persona import Persona
from app.models.user import UserLanguage


async def detect_user_language(
    db: AsyncSession, phone_language: str, country_code: str
) -> Language | None:
    from app.services.geoip_service import build_locale

    locale = build_locale(phone_language, country_code)

    # Try exact locale match
    result = await db.execute(
        select(Language).where(
            Language.locale == locale,
            Language.is_active.is_(True),
            Language.deleted_at.is_(None),
        )
    )
    language = result.scalar_one_or_none()
    if language is not None:
        return language

    # Try matching just the language prefix (e.g., "en" from "en-US")
    lang_prefix = phone_language.split("-")[0] if "-" in phone_language else phone_language
    result = await db.execute(
        select(Language).where(
            Language.locale.startswith(lang_prefix),
            Language.is_active.is_(True),
            Language.deleted_at.is_(None),
            Language.is_default.is_(True),
        )
    )
    language = result.scalar_one_or_none()
    if language is not None:
        return language

    # Try any language with the prefix
    result = await db.execute(
        select(Language)
        .where(
            Language.locale.startswith(lang_prefix),
            Language.is_active.is_(True),
            Language.deleted_at.is_(None),
        )
        .limit(1)
    )
    language = result.scalar_one_or_none()
    if language is not None:
        return language

    # Return fallback
    return await get_fallback_language(db)


async def get_fallback_language(db: AsyncSession) -> Language | None:
    result = await db.execute(
        select(Language).where(
            Language.is_fallback.is_(True),
            Language.is_active.is_(True),
            Language.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_coordinator_for_language(
    db: AsyncSession, language_id: UUID
) -> Persona | None:
    result = await db.execute(
        select(Persona).where(
            Persona.language_id == language_id,
            Persona.type == "coordinator",
            Persona.is_active.is_(True),
            Persona.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_teachers_for_language(
    db: AsyncSession, language_id: UUID
) -> list[Persona]:
    result = await db.execute(
        select(Persona)
        .where(
            Persona.language_id == language_id,
            Persona.type == "teacher",
            Persona.is_active.is_(True),
            Persona.deleted_at.is_(None),
        )
        .order_by(Persona.name)
    )
    return list(result.scalars().all())


async def complete_onboarding(
    db: AsyncSession,
    user_id: UUID,
    native_language_id: UUID,
    target_language_id: UUID,
    teacher_id: UUID,
    teaching_style: str,
    cefr_level: str,
) -> UserLanguage:
    from app.models.user import User

    # Update user's native language
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if user is not None:
        user.native_language_id = native_language_id

    # Create user language entry for the target language
    user_language = UserLanguage(
        user_id=user_id,
        language_id=target_language_id,
        teacher_persona_id=teacher_id,
        teaching_style=teaching_style,
        current_cefr_level=cefr_level,
        is_active=True,
    )
    db.add(user_language)
    await db.flush()
    return user_language
