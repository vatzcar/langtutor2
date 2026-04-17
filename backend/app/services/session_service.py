from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import ChatMessage, Session, SessionTranscript


async def create_session(
    db: AsyncSession,
    user_id: UUID,
    persona_id: UUID,
    session_type: str,
    session_mode: str,
    user_language_id: UUID | None = None,
    cefr_level: str | None = None,
) -> Session:
    session = Session(
        user_id=user_id,
        persona_id=persona_id,
        session_type=session_type,
        session_mode=session_mode,
        user_language_id=user_language_id,
        cefr_level_at_time=cefr_level,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()
    return session


async def end_session(
    db: AsyncSession,
    session_id: UUID,
    duration: int,
    metrics: dict | None = None,
) -> Session:
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise ValueError("Session not found")

    session.ended_at = datetime.now(timezone.utc)
    session.duration_seconds = duration
    if metrics is not None:
        session.performance_metrics = metrics

    await db.flush()
    return session


async def get_user_sessions(
    db: AsyncSession,
    user_id: UUID,
    language_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Session]:
    stmt = select(Session).where(Session.user_id == user_id)
    if language_id is not None:
        from app.models.user import UserLanguage

        stmt = stmt.join(
            UserLanguage, Session.user_language_id == UserLanguage.id
        ).where(UserLanguage.language_id == language_id)
    stmt = stmt.order_by(Session.started_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_session_transcript(
    db: AsyncSession, session_id: UUID
) -> list[SessionTranscript]:
    result = await db.execute(
        select(SessionTranscript)
        .where(SessionTranscript.session_id == session_id)
        .order_by(SessionTranscript.timestamp_offset_ms)
    )
    return list(result.scalars().all())


async def add_chat_message(
    db: AsyncSession, session_id: UUID, sender: str, content: str
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        sender=sender,
        content=content,
    )
    db.add(message)
    await db.flush()
    return message


async def get_chat_messages(
    db: AsyncSession, session_id: UUID
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())


# Aliases expected by route layer
async def list_sessions(
    db: AsyncSession,
    user_id: UUID,
    language_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Session]:
    return await get_user_sessions(db, user_id, language_id, skip, limit)


async def get_transcript(
    db: AsyncSession, session_id: UUID, user_id: UUID
) -> list[SessionTranscript]:
    return await get_session_transcript(db, session_id)


async def detect_locale(client_ip: str | None, phone_language: str) -> str:
    """Simple locale detection — returns phone_language as default fallback."""
    return phone_language


async def complete_onboarding(
    db: AsyncSession,
    user_id: UUID,
    target_language_id: UUID,
    teacher_id: UUID,
    teaching_style: str,
    cefr_level: str,
    name: str,
    date_of_birth=None,
    avatar_id: UUID | None = None,
) -> dict:
    from app.models.user import User, UserLanguage

    # Update user profile
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("User not found")

    user.name = name
    if date_of_birth:
        user.date_of_birth = date_of_birth
    if avatar_id:
        user.avatar_id = avatar_id

    # Create user-language mapping
    user_lang = UserLanguage(
        user_id=user_id,
        language_id=target_language_id,
        teacher_persona_id=teacher_id,
        teaching_style=teaching_style,
        current_cefr_level=cefr_level,
        is_active=True,
    )
    db.add(user_lang)
    await db.flush()

    return {"status": "ok", "user_language_id": str(user_lang.id)}


async def get_session_context(db: AsyncSession, session_id: UUID) -> dict | None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        return None

    transcripts = await get_session_transcript(db, session_id)
    messages = await get_chat_messages(db, session_id)

    return {
        "session_id": str(session.id),
        "user_id": str(session.user_id),
        "session_type": session.session_type,
        "session_mode": session.session_mode,
        "cefr_level": session.cefr_level_at_time,
        "transcript_count": len(transcripts),
        "message_count": len(messages),
    }


async def add_transcript_entry(
    db: AsyncSession,
    session_id: UUID,
    speaker: str,
    content: str,
    offset_ms: int,
) -> SessionTranscript | None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    if result.scalar_one_or_none() is None:
        return None

    entry = SessionTranscript(
        session_id=session_id,
        speaker=speaker,
        content=content,
        timestamp_offset_ms=offset_ms,
    )
    db.add(entry)
    await db.flush()
    return entry


async def update_cefr_level(
    db: AsyncSession,
    session_id: UUID,
    new_level: str,
    progress: float,
    topics: str,
) -> dict | None:
    from app.models.user import UserLanguage

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None or session.user_language_id is None:
        return None

    ul_result = await db.execute(
        select(UserLanguage).where(UserLanguage.id == session.user_language_id)
    )
    user_lang = ul_result.scalar_one_or_none()
    if user_lang is None:
        return None

    user_lang.current_cefr_level = new_level
    user_lang.cefr_progress_percent = progress
    await db.flush()

    return {
        "user_language_id": str(user_lang.id),
        "new_level": new_level,
        "progress": progress,
    }
