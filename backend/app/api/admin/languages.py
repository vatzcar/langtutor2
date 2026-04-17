import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permission
from app.models.admin import AdminUser
from app.schemas.language import LanguageCreate, LanguageUpdate, LanguageResponse
from app.services import language as language_service

router = APIRouter(prefix="/admin/languages", tags=["admin-languages"])

UPLOAD_DIR = Path("uploads/languages")


@router.post("", response_model=LanguageResponse, status_code=201)
async def create_language(
    body: LanguageCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("languages.add")),
):
    return await language_service.create_language(db, body)


@router.get("", response_model=list[LanguageResponse])
async def list_languages(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("languages.view")),
):
    return await language_service.list_languages(db, include_inactive=True)


@router.get("/{language_id}", response_model=LanguageResponse)
async def get_language(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("languages.view")),
):
    lang = await language_service.get_language(db, language_id)
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")
    return lang


@router.patch("/{language_id}", response_model=LanguageResponse)
async def update_language(
    language_id: UUID,
    body: LanguageUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("languages.edit")),
):
    lang = await language_service.update_language(db, language_id, body)
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")
    return lang


@router.delete("/{language_id}", status_code=204)
async def delete_language(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("languages.delete")),
):
    deleted = await language_service.delete_language(db, language_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Language not found")


@router.post("/{language_id}/icon", response_model=LanguageResponse)
async def upload_language_icon(
    language_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("languages.edit")),
):
    lang = await language_service.get_language(db, language_id)
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix if file.filename else ".png"
    file_path = UPLOAD_DIR / f"{language_id}{ext}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    icon_url = f"/uploads/languages/{language_id}{ext}"
    return await language_service.update_language(
        db, language_id, LanguageUpdate(icon_url=icon_url)  # type: ignore
    )
