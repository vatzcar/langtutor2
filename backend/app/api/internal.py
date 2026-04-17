from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import session as session_service

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/session-context/{session_id}")
async def get_session_context(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    context = await session_service.get_session_context(db, session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")
    return context


@router.post("/session/{session_id}/transcript")
async def add_transcript_entry(
    session_id: UUID,
    speaker: str = Query(...),
    content: str = Query(...),
    offset_ms: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    entry = await session_service.add_transcript_entry(
        db, session_id, speaker=speaker, content=content, offset_ms=offset_ms
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    return entry


@router.post("/session/{session_id}/update-cefr")
async def update_cefr_level(
    session_id: UUID,
    new_level: str = Query(...),
    progress: float = Query(...),
    topics: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    result = await session_service.update_cefr_level(
        db, session_id, new_level=new_level, progress=progress, topics=topics
    )
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result
