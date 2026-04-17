from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.session import SessionResponse, TranscriptResponse
from app.services import session as session_service
from app.services import usage as usage_service
from app.services import persona as persona_service
from app.services import livekit as livekit_service

router = APIRouter(prefix="/mobile/sessions", tags=["mobile-sessions"])


class StartSessionRequest(BaseModel):
    session_type: str
    session_mode: str
    language_id: UUID | None = None


class EndSessionRequest(BaseModel):
    duration_seconds: int


class OnboardingStartRequest(BaseModel):
    phone_language: str


class OnboardingCompleteRequest(BaseModel):
    target_language_id: UUID
    teacher_id: UUID
    teaching_style: str
    cefr_level: str
    name: str
    date_of_birth: date | None = None
    avatar_id: UUID | None = None


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    language_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await session_service.list_sessions(
        db, current_user.id, language_id=language_id, skip=skip, limit=limit
    )


@router.get("/{session_id}/transcript", response_model=list[TranscriptResponse])
async def get_transcript(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await session_service.get_transcript(db, session_id, current_user.id)


@router.post("/start")
async def start_session(
    body: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check usage limits
    limit_info = await usage_service.check_limit(db, current_user.id, body.session_type)
    if not limit_info["allowed"]:
        raise HTTPException(status_code=403, detail="Usage limit reached for this feature")

    # Get persona for the language
    persona = await persona_service.get_teacher_for_language(db, body.language_id)
    if not persona:
        raise HTTPException(status_code=404, detail="No teacher found for this language")

    # Create session
    session = await session_service.create_session(
        db,
        user_id=current_user.id,
        persona_id=persona.id,
        session_type=body.session_type,
        session_mode=body.session_mode,
        user_language_id=body.language_id,
    )

    # Create LiveKit room for call sessions
    room_name = f"session-{session.id}"
    livekit_token = await livekit_service.create_room_and_token(
        room_name=room_name,
        participant_name=current_user.name,
        session_id=str(session.id),
    )

    return {
        "session_id": session.id,
        "livekit_token": livekit_token,
        "room_name": room_name,
    }


@router.post("/{session_id}/end")
async def end_session(
    session_id: UUID,
    body: EndSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        session = await session_service.end_session(db, session_id, body.duration_seconds)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    # Record usage (convert seconds to minutes)
    await usage_service.record_usage(
        db, current_user.id, session.session_type, body.duration_seconds / 60.0
    )

    return {"status": "ok"}


@router.get("/usage/check")
async def check_usage(
    feature: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed = await usage_service.check_limit(db, current_user.id, feature)
    return {"allowed": allowed, "feature": feature}


@router.post("/onboarding/start")
async def onboarding_start(
    body: OnboardingStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Detect locale via GeoIP from client IP
    client_ip = request.client.host if request.client else None
    detected_language = await session_service.detect_locale(client_ip, body.phone_language)

    # Get coordinator persona
    coordinator = await persona_service.get_coordinator(db)

    room_name = f"onboarding-{current_user.id}"
    await livekit_service.create_room_and_token(
        room_name=room_name,
        participant_name=current_user.name,
        session_id=f"onboarding-{current_user.id}",
    )

    return {
        "room_name": room_name,
        "detected_language": detected_language,
        "coordinator": coordinator,
    }


@router.post("/onboarding/complete")
async def onboarding_complete(
    body: OnboardingCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await session_service.complete_onboarding(
        db,
        user_id=current_user.id,
        target_language_id=body.target_language_id,
        teacher_id=body.teacher_id,
        teaching_style=body.teaching_style,
        cefr_level=body.cefr_level,
        name=body.name,
        date_of_birth=body.date_of_birth,
        avatar_id=body.avatar_id,
    )
    return result
