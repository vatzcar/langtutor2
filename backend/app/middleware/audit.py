"""Audit middleware: transparently logs every successful admin mutation.

Captures POST/PATCH/PUT/DELETE requests on `/api/v1/admin/*` that return a
2xx response and writes an `AuditLog` row with the actor (from JWT),
parsed resource_type / resource_id from the URL path, and the client IP.

Any failure in the middleware itself is swallowed — an audit log miss must
never break the actual request.
"""
from __future__ import annotations

import logging
import re
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.database import async_session_factory
from app.models.audit import AuditLog
from app.utils.security import verify_token

logger = logging.getLogger(__name__)

# /api/v1/admin/<resource>[/<id>][/<sub-action>]
_RESOURCE_RE = re.compile(
    r"^/api/v1/admin/(?P<resource>[a-z-]+)"
    r"(?:/(?P<id>[^/]+))?"
    r"(?:/(?P<sub>[a-z-]+))?/?$"
)

_MUTATION_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        try:
            await self._maybe_log(request, response)
        except Exception:  # pragma: no cover — audit is never fatal
            logger.exception("AuditMiddleware failed to record log")

        return response

    async def _maybe_log(self, request: Request, response: Response) -> None:
        if request.method not in _MUTATION_METHODS:
            return
        if not (200 <= response.status_code < 300):
            return

        path = request.url.path
        if not path.startswith("/api/v1/admin/"):
            return

        # Who?
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return
        token = auth_header.split(" ", 1)[1]
        payload = verify_token(token)
        if not payload or payload.get("type") != "admin":
            return
        try:
            actor_id = UUID(payload["sub"])
        except (KeyError, ValueError):
            return

        # What?
        match = _RESOURCE_RE.match(path)
        if not match:
            return
        resource_type = match.group("resource")
        raw_id = match.group("id")
        sub_action = match.group("sub")

        method_to_verb = {
            "POST": "create",
            "PATCH": "update",
            "PUT": "update",
            "DELETE": "delete",
        }
        verb = method_to_verb[request.method]

        # Sub-paths override the verb: /admin/users/{id}/ban → "ban"
        if sub_action:
            verb = sub_action.replace("-", "_")

        action = f"{resource_type}.{verb}"

        resource_id: UUID | None = None
        if raw_id:
            try:
                resource_id = UUID(raw_id)
            except ValueError:
                resource_id = None

        client_ip = request.client.host if request.client else None

        async with async_session_factory() as db:
            db.add(
                AuditLog(
                    actor_type="admin",
                    actor_id=actor_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=client_ip,
                )
            )
            await db.commit()
