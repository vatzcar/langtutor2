from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.admin import AdminUser
from app.models.user import User
from app.utils.security import create_access_token, verify_password


async def verify_google_token(id_token: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("aud") != settings.google_client_id:
            return None
        return {
            "email": data["email"],
            "name": data.get("name", data.get("email", "")),
            "sub": data["sub"],
        }


async def verify_apple_token(id_token: str) -> dict | None:
    try:
        from jose import jwt as jose_jwt

        async with httpx.AsyncClient() as client:
            resp = await client.get("https://appleid.apple.com/auth/keys")
            if resp.status_code != 200:
                return None
            apple_jwks = resp.json()

        unverified = jose_jwt.get_unverified_claims(id_token)
        return {
            "email": unverified.get("email", ""),
            "name": unverified.get("name", unverified.get("email", "")),
            "sub": unverified.get("sub", ""),
        }
    except Exception:
        return None


async def social_login(
    db: AsyncSession, provider: str, id_token: str
) -> tuple[User, str, bool]:
    if provider == "google":
        token_data = await verify_google_token(id_token)
    elif provider == "apple":
        token_data = await verify_apple_token(id_token)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    if token_data is None:
        raise ValueError("Invalid or expired social token")

    email = token_data["email"]
    name = token_data["name"]
    provider_id = token_data["sub"]

    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    is_new = False

    if user is None:
        user = User(
            email=email,
            name=name,
            auth_provider=provider,
            auth_provider_id=provider_id,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        is_new = True

    jwt_token = create_access_token(
        data={"sub": str(user.id), "type": "user"}
    )
    return user, jwt_token, is_new


async def admin_login(
    db: AsyncSession, email: str, password: str
) -> tuple[AdminUser, str]:
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.email == email, AdminUser.deleted_at.is_(None)
        )
    )
    admin = result.scalar_one_or_none()

    if admin is None or not verify_password(password, admin.password_hash):
        raise ValueError("Invalid email or password")

    if not admin.is_active:
        raise ValueError("Admin account is inactive")

    jwt_token = create_access_token(
        data={"sub": str(admin.id), "type": "admin"}
    )
    return admin, jwt_token
