from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permission
from app.models.admin import AdminUser
from app.services import report as report_service

router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])


@router.get("/registrations")
async def registration_report(
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("reports.view")),
):
    return await report_service.get_registration_report(db, from_date=from_date, to_date=to_date)


@router.get("/active-users")
async def active_users_report(
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("reports.view")),
):
    return await report_service.get_active_users_report(db, from_date=from_date, to_date=to_date)


@router.get("/engagement")
async def engagement_report(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("reports.view")),
):
    return await report_service.get_engagement_report(db)


@router.get("/language-analytics")
async def language_analytics(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("reports.view")),
):
    return await report_service.get_language_analytics(db)
