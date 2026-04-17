"""Database seed script for LangTutor."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

from passlib.hash import bcrypt
from sqlalchemy import select

from app.database import Base, async_session_factory, engine
from app.models.admin import AdminRole, AdminUser
from app.models.plan import Plan


async def seed() -> None:
    """Create all tables and seed initial data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # ------------------------------------------------------------------
        # Seed plans
        # ------------------------------------------------------------------
        existing_plans = (await session.execute(select(Plan))).scalars().all()
        if not existing_plans:
            plans = [
                Plan(
                    id=uuid.uuid4(),
                    name="Free",
                    slug="free",
                    price_monthly=Decimal("0.00"),
                    price_yearly=Decimal("0.00"),
                    text_learning_limit_minutes=0,
                    voice_call_limit_minutes=30,
                    video_call_limit_minutes=0,
                    agentic_voice_limit_monthly=0,
                    coordinator_video_limit_monthly=0,
                    is_active=True,
                ),
                Plan(
                    id=uuid.uuid4(),
                    name="Pro",
                    slug="pro",
                    price_monthly=Decimal("4.99"),
                    price_yearly=Decimal("49.99"),
                    text_learning_limit_minutes=0,
                    voice_call_limit_minutes=0,  # 0 = unlimited
                    video_call_limit_minutes=15,
                    agentic_voice_limit_monthly=5,
                    coordinator_video_limit_monthly=2,
                    is_active=True,
                ),
                Plan(
                    id=uuid.uuid4(),
                    name="Ultra",
                    slug="ultra",
                    price_monthly=Decimal("9.99"),
                    price_yearly=Decimal("99.99"),
                    text_learning_limit_minutes=0,
                    voice_call_limit_minutes=0,
                    video_call_limit_minutes=0,
                    agentic_voice_limit_monthly=0,
                    coordinator_video_limit_monthly=0,
                    is_active=True,
                ),
            ]
            session.add_all(plans)
            print(f"Seeded {len(plans)} plans.")
        else:
            print("Plans already exist, skipping.")

        # ------------------------------------------------------------------
        # Seed super_admin role
        # ------------------------------------------------------------------
        existing_role = (
            await session.execute(
                select(AdminRole).where(AdminRole.name == "super_admin")
            )
        ).scalar_one_or_none()

        if not existing_role:
            all_permissions = [
                "users:read",
                "users:write",
                "users:delete",
                "users:ban",
                "admins:read",
                "admins:write",
                "admins:delete",
                "plans:read",
                "plans:write",
                "plans:delete",
                "subscriptions:read",
                "subscriptions:write",
                "languages:read",
                "languages:write",
                "personas:read",
                "personas:write",
                "personas:delete",
                "sessions:read",
                "sessions:delete",
                "usage:read",
                "audit:read",
                "settings:read",
                "settings:write",
            ]
            role = AdminRole(
                id=uuid.uuid4(),
                name="super_admin",
                permissions=all_permissions,
            )
            session.add(role)
            await session.flush()
            print("Seeded super_admin role.")
        else:
            role = existing_role
            print("super_admin role already exists, skipping.")

        # ------------------------------------------------------------------
        # Seed admin user
        # ------------------------------------------------------------------
        existing_admin = (
            await session.execute(
                select(AdminUser).where(AdminUser.email == "admin@langtutor.com")
            )
        ).scalar_one_or_none()

        if not existing_admin:
            admin = AdminUser(
                id=uuid.uuid4(),
                email="admin@langtutor.com",
                name="Admin",
                password_hash=bcrypt.hash("admin123"),
                role_id=role.id,
                is_active=True,
            )
            session.add(admin)
            print("Seeded admin user (admin@langtutor.com / admin123).")
        else:
            print("Admin user already exists, skipping.")

        await session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
