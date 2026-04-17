"""Granular permission definitions for the admin console.

Permissions use dotted `feature.action` format.
"""

ALL_PERMISSIONS: list[str] = [
    "languages.view",
    "languages.add",
    "languages.edit",
    "languages.delete",
    "personas.view",
    "personas.add",
    "personas.edit",
    "personas.delete",
    "users.view",
    "users.add",
    "users.edit",
    "users.delete",
    "admins.view",
    "admins.add",
    "admins.edit",
    "admins.delete",
    "plans.manage",
    "reports.view",
    "logs.view",
]

ALL_PERMISSIONS_SET: frozenset[str] = frozenset(ALL_PERMISSIONS)


def is_superadmin_permissions(perms: list[str]) -> bool:
    """Return True iff ``perms`` contains every permission in ALL_PERMISSIONS."""
    if not perms:
        return False
    return frozenset(perms) >= ALL_PERMISSIONS_SET
