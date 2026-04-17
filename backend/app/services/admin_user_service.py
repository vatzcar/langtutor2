from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AdminRole, AdminUser
from app.schemas.admin import AdminUserCreate, AdminUserUpdate
from app.utils.permissions import is_superadmin_permissions
from app.utils.security import hash_password


async def _count_super_admins(db: AsyncSession) -> int:
    """Count active (is_active=True, deleted_at IS NULL) admin users whose role
    has the full super-admin permission set."""
    stmt = (
        select(AdminUser)
        .join(AdminRole, AdminUser.role_id == AdminRole.id)
        .where(
            AdminUser.is_active.is_(True),
            AdminUser.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    admins = result.scalars().all()
    return sum(
        1
        for a in admins
        if is_superadmin_permissions(list((a.role.permissions or [])))
    )


async def _is_super_admin(admin: AdminUser) -> bool:
    return is_superadmin_permissions(list((admin.role.permissions or [])))


async def list_admin_users(
    db: AsyncSession, skip: int = 0, limit: int = 50
) -> list[AdminUser]:
    stmt = (
        select(AdminUser)
        .where(AdminUser.deleted_at.is_(None))
        .offset(skip)
        .limit(limit)
        .order_by(AdminUser.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_admin_user(
    db: AsyncSession, admin_id: UUID
) -> AdminUser | None:
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.id == admin_id, AdminUser.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def create_admin_user(
    db: AsyncSession, data: AdminUserCreate
) -> AdminUser:
    admin = AdminUser(
        email=data.email,
        name=data.name,
        password_hash=hash_password(data.password),
        role_id=data.role_id,
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    return admin


async def _role_is_super(db: AsyncSession, role_id: UUID) -> bool:
    role_res = await db.execute(
        select(AdminRole).where(AdminRole.id == role_id)
    )
    role = role_res.scalar_one_or_none()
    if role is None:
        return False
    return is_superadmin_permissions(list(role.permissions or []))


async def update_admin_user(
    db: AsyncSession, admin_id: UUID, data: AdminUserUpdate
) -> AdminUser | None:
    admin = await get_admin_user(db, admin_id)
    if admin is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    # Guard role changes: if switching away from super-admin role and this
    # admin is currently an active super-admin, prevent leaving zero supers.
    if "role_id" in update_data and update_data["role_id"] is not None:
        new_role_id = update_data["role_id"]
        if (
            admin.is_active
            and admin.deleted_at is None
            and await _is_super_admin(admin)
            and not await _role_is_super(db, new_role_id)
        ):
            total = await _count_super_admins(db)
            if total <= 1:
                raise ValueError(
                    "Cannot change role: this is the last active super admin user"
                )

    # Guard deactivation via PATCH.
    if "is_active" in update_data and update_data["is_active"] is False:
        if (
            admin.is_active
            and admin.deleted_at is None
            and await _is_super_admin(admin)
        ):
            total = await _count_super_admins(db)
            if total <= 1:
                raise ValueError(
                    "Cannot deactivate the last active super admin user"
                )

    for key, value in update_data.items():
        setattr(admin, key, value)

    await db.flush()
    return admin


async def toggle_admin_active(
    db: AsyncSession, admin_id: UUID, is_active: bool
) -> AdminUser | None:
    admin = await get_admin_user(db, admin_id)
    if admin is None:
        return None

    if (
        is_active is False
        and admin.is_active
        and admin.deleted_at is None
        and await _is_super_admin(admin)
    ):
        total = await _count_super_admins(db)
        if total <= 1:
            raise ValueError(
                "Cannot deactivate the last active super admin user"
            )

    admin.is_active = is_active
    await db.flush()
    return admin


async def delete_admin_user(db: AsyncSession, admin_id: UUID) -> bool:
    admin = await get_admin_user(db, admin_id)
    if admin is None:
        return False

    if (
        admin.is_active
        and admin.deleted_at is None
        and await _is_super_admin(admin)
    ):
        total = await _count_super_admins(db)
        if total <= 1:
            raise ValueError(
                "Cannot delete the last active super admin user"
            )

    admin.deleted_at = datetime.now(timezone.utc)
    admin.is_active = False
    await db.flush()
    return True
