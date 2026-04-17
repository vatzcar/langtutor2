from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session, ChatMessage
from app.schemas.session import ChatMessageCreate


async def get_messages(db: AsyncSession, session_id: UUID, user_id: UUID) -> list:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()


async def send_message(
    db: AsyncSession, session_id: UUID, user_id: UUID, body: ChatMessageCreate
) -> ChatMessage | None:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return None

    msg = ChatMessage(
        session_id=session_id,
        sender="user",
        content=body.content,
    )
    db.add(msg)
    await db.flush()
    return msg
