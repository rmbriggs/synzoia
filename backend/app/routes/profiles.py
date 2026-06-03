"""HTTP layer for /api/profiles.

Read endpoint lists every user; write endpoint creates a new profile +
returns its server-issued token. The POST handler was previously
defined inline in main.py — promoted here so both verbs live in one
router and the schema stays cohesive."""

import re
import secrets
import string
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app import db
from backend.app.errors import AppError
from backend.app.schemas.profiles import ProfileListResponse
from backend.app.services import profiles as svc

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

# Username: 1-30 chars of [A-Za-z0-9_]. Matches the migration's
# char_length(username) between 1 and 30 check and gives a readable
# 422 message instead of letting the DB reject it.
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,30}$")


class CreateProfileRequest(BaseModel):
    username: str = Field(min_length=1, max_length=30)


class ProfileResponse(BaseModel):
    """Matches the original handler exactly so existing test_profiles.py
    assertions keep passing — FastAPI serializes datetime → ISO string."""
    username: str
    token: str
    join_date: datetime


def _generate_token() -> str:
    """4 groups of 4 uppercase letters joined by dashes, e.g.
    'AHDE-VHSE-CNCX-HELJ'. 19 chars total, ~75 bits of entropy —
    long enough that collisions are not a practical concern and
    short enough that the user can re-type from memory if needed.

    Stored with dashes; the iOS Shortcut pastes the exact string
    the website displayed, so auth is a direct string match — no
    normalization required."""
    groups = [
        "".join(secrets.choice(string.ascii_uppercase) for _ in range(4))
        for _ in range(4)
    ]
    return "-".join(groups)


@router.get("", response_model=ProfileListResponse)
def list_profiles() -> ProfileListResponse:
    """Read: every user, sorted alphabetically by username."""
    with db.get_engine().connect() as conn:
        return svc.list_profiles(conn)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
def create_profile(req: CreateProfileRequest) -> ProfileResponse:
    """Write: sign up, get back a token. Usernames are normalized to
    lowercase so 'Sam' and 'SAM' can't both register. Username uniqueness
    is enforced at the DB level; collisions surface as 409 'username_taken'."""
    username = req.username.lower()
    if not _USERNAME_RE.match(username):
        raise AppError(
            422,
            "invalid_username",
            "Username must be 1-30 characters of letters, digits, or underscore.",
        )

    token = _generate_token()
    try:
        with db.get_engine().begin() as conn:
            row = (
                conn.execute(
                    text(
                        "INSERT INTO profiles (username, token) "
                        "VALUES (:username, :token) "
                        "RETURNING username, token, join_date"
                    ),
                    {"username": username, "token": token},
                )
                .mappings()
                .one()
            )
    except IntegrityError as e:
        # Either username collided (expected) or token collided (1-in-2^128).
        # Both surface as a unique-violation; treat as username-taken since
        # token collisions are not user-actionable and shouldn't happen.
        raise AppError(
            409,
            "username_taken",
            "That username is already taken.",
        ) from e

    return ProfileResponse(**dict(row))
