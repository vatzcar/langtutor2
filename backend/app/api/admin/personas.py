import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permission
from app.models.admin import AdminUser
from app.schemas.persona import PersonaCreate, PersonaUpdate, PersonaResponse
from app.services import persona as persona_service

router = APIRouter(prefix="/admin/personas", tags=["admin-personas"])

UPLOAD_DIR = Path("uploads/personas")


@router.post("", response_model=PersonaResponse, status_code=201)
async def create_persona(
    body: PersonaCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("personas.add")),
):
    try:
        return await persona_service.create_persona(db, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[PersonaResponse])
async def list_personas(
    language_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("personas.view")),
):
    return await persona_service.list_personas(db, language_id=language_id)


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("personas.view")),
):
    persona = await persona_service.get_persona(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.patch("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: UUID,
    body: PersonaUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("personas.edit")),
):
    persona = await persona_service.update_persona(db, persona_id, body)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(
    persona_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("personas.delete")),
):
    deleted = await persona_service.delete_persona(db, persona_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Persona not found")


@router.post("/{persona_id}/image", response_model=PersonaResponse)
async def upload_persona_image(
    persona_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("personas.edit")),
):
    persona = await persona_service.get_persona(db, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix if file.filename else ".png"
    file_path = UPLOAD_DIR / f"{persona_id}{ext}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    image_url = f"/uploads/personas/{persona_id}{ext}"
    return await persona_service.update_persona(
        db, persona_id, PersonaUpdate(image_url=image_url)  # type: ignore
    )
