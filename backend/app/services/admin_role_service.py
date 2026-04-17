from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AdminRole
from app.schemas.admin import AdminRoleCreate
from app.utils.permissions import is_superadmin_permissions


async def _count_other_superadmin_roles(
    db: AsyncSession, exclude_role_id: UUID
) -> int:
    """Count admin roles (other than ``exclude_role_id``) whose permissions
    include the full super-admin permission set."""
    result = await db.execute(
        select(AdminRole).where(AdminRole.id != exclude_role_id)
    )
    roles = result.scalars().all()
    return sum(
        1 for r in roles if is_superadmin_permissions(list(r.permissions or []))
    )


async def create_role(db: AsyncSession, data: AdminRoleCreate) -> AdminRole:
    role = AdminRole(name=data.name, permissions=data.permissions)
    db.add(role)
    await db.flush()
    return role


async def list_roles(db: AsyncSession) -> list[AdminRole]:
    result = await db.execute(
        select(AdminRole).order_by(AdminRole.created_at.desc())
    )
    return list(result.scalars().all())


async def get_role(db: AsyncSession, role_id: UUID) -> AdminRole | None:
    result = await db.execute(select(AdminRole).where(AdminRole.id == role_id))
    return result.scalar_one_or_none()


async def update_role(
    db: AsyncSession, role_id: UUID, data: AdminRoleCreate
) -> AdminRole | None:
    role = await get_role(db, role_id)
    if role is None:
        return None

    existing_is_super = is_superadmin_permissions(list(role.permissions or []))
    new_is_super = is_superadmin_permissions(list(data.permissions or []))

    if existing_is_super and not new_is_super:
        others = await _count_other_superadmin_roles(db, role_id)
        if others == 0:
            raise ValueError(
                "Cannot remove super-admin permissions from the last super admin role"
            )

    role.name = data.name
    role.permissions = data.permissions
    await db.flush()
    return role


async def delete_role(db: AsyncSession, role_id: UUID) -> bool:
    role = await get_role(db, role_id)
    if role is None:
        return False

    if is_superadmin_permissions(list(role.permissions or [])):
        others = await _count_other_superadmin_roles(db, role_id)
        if others == 0:
            raise ValueError("Cannot delete the last super admin role")

    await db.delete(role)
    await db.flush()
    return True
