"""Ensure existing Super Admin role has `manage_admins` permission.

Run this once after pulling Feature Extension 1 changes if your database
was seeded before `manage_admins` existed.
"""
import asyncio

from sqlalchemy import select

from app.database import async_session_factory
from app.models.admin import AdminRole


async def upgrade():
    async with async_session_factory() as db:
        result = await db.execute(
            select(AdminRole).where(AdminRole.name == "Super Admin")
        )
        role = result.scalar_one_or_none()
        if role is None:
            print("No Super Admin role found — run seed.py first.")
            return

        perms = list(role.permissions or [])
        if "manage_admins" in perms:
            print("manage_admins permission already present. Nothing to do.")
            return

        perms.append("manage_admins")
        role.permissions = perms
        await db.commit()
        print(f"Added manage_admins to Super Admin role. Now: {perms}")


if __name__ == "__main__":
    asyncio.run(upgrade())
