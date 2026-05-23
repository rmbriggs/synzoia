"""Bearer-token authentication.

The iOS Shortcut (and any other writer) authenticates by sending the
user's personal token in the `Authorization: Bearer <token>` header.
This module exposes a FastAPI dependency, `require_user`, that parses
the header, looks the token up in `profiles`, and returns the
resolved `user_id`.

Per CLAUDE.md: `user_id` is resolved from the token, never from the
request body.
"""

from typing import Optional

from fastapi import Header, status
from sqlalchemy import text

from backend.app import db
from backend.app.errors import AppError


def _unauthenticated() -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED,
        "unauthenticated",
        "Missing or invalid Authorization header. Expected 'Bearer <token>'.",
    )


def require_user(authorization: Optional[str] = Header(default=None)) -> int:
    """FastAPI dependency. Parses `Authorization: Bearer <token>` and
    returns the matching `profiles.id`. Raises `AppError(401)` on any
    missing / malformed / unknown-token case (callers shouldn't be able
    to tell which one — that's a deliberate information-leak guard)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthenticated()

    token = authorization[len("Bearer "):].strip()
    if not token:
        raise _unauthenticated()

    with db.get_engine().connect() as conn:
        row = (
            conn.execute(
                text("SELECT id FROM profiles WHERE token = :token"),
                {"token": token},
            )
            .mappings()
            .first()
        )

    if row is None:
        raise _unauthenticated()

    return int(row["id"])
