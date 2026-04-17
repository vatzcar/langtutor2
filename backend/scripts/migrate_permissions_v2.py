"""Migrate admin role permissions from coarse strings to dotted ``feature.action`` form.

Idempotent: running twice is a no-op.

Old -> new:
    manage_languages -> languages.view, languages.add, languages.edit, languages.delete
    manage_personas  -> personas.view, personas.add, personas.edit, personas.delete
    manage_users     -> users.view, users.add, users.edit, users.delete
    manage_admins    -> admins.view, admins.add, admins.edit, admins.delete
    manage_plans     -> plans.manage
    view_reports     -> reports.view
    view_logs        -> logs.view
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.database import async_session_factory
from app.models.admin import AdminRole


OLD_TO_NEW: dict[str, list[str]] = {
    "manage_languages": [
        "languages.view",
        "languages.add",
        "languages.edit",
        "languages.delete",
    ],
    "manage_personas": [
        "personas.view",
        "personas.add",
        "personas.edit",
        "personas.delete",
    ],
    "manage_users": [
        "users.view",
        "users.add",
        "users.edit",
        "users.delete",
    ],
    "manage_admins": [
        "admins.view",
        "admins.add",
        "admins.edit",
        "admins.delete",
    ],
    "manage_plans": ["plans.manage"],
    "view_reports": ["reports.view"],
    "view_logs": ["logs.view"],
}

OLD_KEYS = set(OLD_TO_NEW.keys())


def migrate_list(perms: list[str]) -> list[str]:
    """Return the permission list in new-format, preserving order and dedup."""
    out: list[str] = []
    seen: set[str] = set()
    for p in perms:
        mapped = OLD_TO_NEW.get(p)
        if mapped is not None:
            for np in mapped:
                if np not in seen:
                    seen.add(np)
                    out.append(np)
        else:
            if p not in seen:
                seen.add(p)
                out.append(p)
    return out


async def migrate() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(AdminRole))
        roles = list(result.scalars().all())

        changed_count = 0
        for role in roles:
            current = list(role.permissions or [])
            has_old = any(p in OLD_KEYS for p in current)
            if not has_old:
                print(f"[skip] role={role.name!r} already new-format")
                continue

            new_perms = migrate_list(current)
            if new_perms == current:
                print(f"[skip] role={role.name!r} no change")
                continue

            print(f"[update] role={role.name!r}")
            print(f"    before: {current}")
            print(f"    after:  {new_perms}")
            role.permissions = new_perms
            flag_modified(role, "permissions")
            changed_count += 1

        await db.commit()
        print(f"\nDone. Updated {changed_count} role(s).")


if __name__ == "__main__":
    asyncio.run(migrate())
