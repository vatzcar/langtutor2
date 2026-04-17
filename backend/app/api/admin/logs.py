from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import require_permission
from app.models.admin import AdminUser
from app.schemas.audit import AuditLogResponse
from app.services import audit_log as log_service

router = APIRouter(prefix="/admin/logs", tags=["admin-logs"])


@router.get("", response_model=list[AuditLogResponse])
async def get_logs(
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    actor_type: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_permission("logs.view")),
):
    return await log_service.get_logs(
        db,
        skip=skip,
        limit=limit,
        action=action,
        actor_type=actor_type,
        from_date=from_date,
        to_date=to_date,
        sort_by=sort_by,
        sort_order=sort_order,
    )
