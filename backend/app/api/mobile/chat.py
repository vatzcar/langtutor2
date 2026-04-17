from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.session import ChatMessageCreate, ChatMessageResponse
from app.services import chat as chat_service

router = APIRouter(prefix="/mobile/chat", tags=["mobile-chat"])


@router.get("/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await chat_service.get_messages(db, session_id, current_user.id)


@router.post("/{session_id}/messages", response_model=ChatMessageResponse, status_code=201)
async def send_message(
    session_id: UUID,
    body: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msg = await chat_service.send_message(db, session_id, current_user.id, body)
    if not msg:
        raise HTTPException(status_code=404, detail="Session not found")
    return msg
