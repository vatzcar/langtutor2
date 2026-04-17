"""Upgrade plan rows to Feature Extension 3 semantics.

- Free: video & agentic & coordinator → -1 (Not Available); text → 0 (unlimited)
- Basic → Pro (renamed); agentic/coordinator set
- Premium → Ultra (renamed); unlimited voice/text/agentic/coordinator
- If Pro/Ultra already exist (fresh seed), values are re-applied.

Safe to run multiple times.
"""
import asyncio

from sqlalchemy import select

from app.database import async_session_factory
from app.models.plan import Plan


async def upgrade():
    async with async_session_factory() as db:
        # Load all plans
        result = await db.execute(select(Plan))
        plans = {p.slug: p for p in result.scalars().all()}

        # --- Free ---
        free = plans.get("free")
        if free is not None:
            free.voice_call_limit_minutes = 5
            free.video_call_limit_minutes = -1
            free.text_learning_limit_minutes = 0
            free.agentic_voice_limit_monthly = -1
            free.coordinator_video_limit_monthly = -1
            print(f"Updated Free plan")

        # --- Basic → Pro rename + values ---
        pro = plans.get("pro") or plans.get("basic")
        if pro is not None:
            pro.slug = "pro"
            pro.name = "Pro"
            pro.price_monthly = 9.99
            pro.price_yearly = 99.99
            pro.voice_call_limit_minutes = 30
            pro.video_call_limit_minutes = 15
            pro.text_learning_limit_minutes = 0
            pro.agentic_voice_limit_monthly = 60
            pro.coordinator_video_limit_monthly = 30
            print(f"Updated/renamed Pro plan")

        # --- Premium → Ultra rename + values ---
        ultra = plans.get("ultra") or plans.get("premium")
        if ultra is not None:
            ultra.slug = "ultra"
            ultra.name = "Ultra"
            ultra.price_monthly = 19.99
            ultra.price_yearly = 199.99
            ultra.voice_call_limit_minutes = 0
            ultra.video_call_limit_minutes = 60
            ultra.text_learning_limit_minutes = 0
            ultra.agentic_voice_limit_monthly = 0
            ultra.coordinator_video_limit_monthly = 0
            print(f"Updated/renamed Ultra plan")

        await db.commit()
        print("Plan upgrade complete.")


if __name__ == "__main__":
    asyncio.run(upgrade())
