"""Database seed script for development data."""
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, engine, Base
from app.models.admin import AdminRole, AdminUser
from app.models.language import Language
from app.models.persona import Persona
from app.models.plan import Plan
from app.utils.permissions import ALL_PERMISSIONS
from app.utils.security import hash_password


async def seed():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # --- Admin roles ---
        superadmin_role = AdminRole(
            name="Super Admin",
            permissions=list(ALL_PERMISSIONS),
        )
        db.add(superadmin_role)
        await db.flush()

        # --- Admin user ---
        admin = AdminUser(
            email="admin@langtutor.app",
            name="Admin",
            password_hash=hash_password("admin123"),
            role_id=superadmin_role.id,
            is_active=True,
        )
        db.add(admin)

        # --- Languages ---
        english = Language(
            name="English",
            locale="en",
            is_default=True,
            is_fallback=True,
            is_active=True,
        )
        spanish = Language(
            name="Spanish",
            locale="es",
            is_default=False,
            is_fallback=False,
            is_active=True,
        )
        french = Language(
            name="French",
            locale="fr",
            is_default=False,
            is_fallback=False,
            is_active=True,
        )
        db.add_all([english, spanish, french])
        await db.flush()

        # --- Personas ---
        coordinator = Persona(
            name="Luna",
            language_id=english.id,
            gender="female",
            type="coordinator",
            is_active=True,
        )
        teacher_en = Persona(
            name="James",
            language_id=english.id,
            gender="male",
            type="teacher",
            teaching_style="friendly_structured",
            is_active=True,
        )
        teacher_es = Persona(
            name="Maria",
            language_id=spanish.id,
            gender="female",
            type="teacher",
            teaching_style="casual_friendly",
            is_active=True,
        )
        teacher_fr = Persona(
            name="Pierre",
            language_id=french.id,
            gender="male",
            type="teacher",
            teaching_style="formal_structured",
            is_active=True,
        )
        db.add_all([coordinator, teacher_en, teacher_es, teacher_fr])

        # --- Plans ---
        free_plan = Plan(
            name="Free",
            slug="free",
            price_monthly=0,
            price_yearly=0,
            # -1 = Not Available, 0 = Unlimited, >0 = minutes
            voice_call_limit_minutes=5,
            video_call_limit_minutes=-1,   # Not Available on Free
            text_learning_limit_minutes=0,  # Unlimited text
            agentic_voice_limit_monthly=-1,
            coordinator_video_limit_monthly=-1,
            is_active=True,
        )
        pro_plan = Plan(
            name="Pro",
            slug="pro",
            price_monthly=9.99,
            price_yearly=99.99,
            voice_call_limit_minutes=30,
            video_call_limit_minutes=15,
            text_learning_limit_minutes=0,  # Unlimited
            agentic_voice_limit_monthly=60,
            coordinator_video_limit_monthly=30,
            is_active=True,
        )
        ultra_plan = Plan(
            name="Ultra",
            slug="ultra",
            price_monthly=19.99,
            price_yearly=199.99,
            voice_call_limit_minutes=0,     # Unlimited
            video_call_limit_minutes=60,
            text_learning_limit_minutes=0,  # Unlimited
            agentic_voice_limit_monthly=0,  # Unlimited
            coordinator_video_limit_monthly=0,
            is_active=True,
        )
        db.add_all([free_plan, pro_plan, ultra_plan])

        await db.commit()
        print("Seed data created successfully!")
        print(f"  Admin: admin@langtutor.app / admin123")
        print(f"  Languages: English, Spanish, French")
        print(f"  Plans: Free, Pro, Ultra")


if __name__ == "__main__":
    asyncio.run(seed())
