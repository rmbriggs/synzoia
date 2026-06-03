"""HTTP layer for /api/profiles.

Read endpoint lists every user; write endpoint links the caller's
Supabase Auth identity to a new profile row + returns the
machine-token the iOS Shortcut needs.

Auth flow for signup (post-C2):

  1. Frontend calls `supabase.auth.signUp(email, password)` —
     Supabase creates a user in its `auth.users` table and returns
     a JWT session.
  2. Frontend immediately calls POST /api/profiles with that JWT
     in the Authorization header and the chosen username in the
     body.
  3. This endpoint verifies the JWT (via require_supabase_uid),
     extracts the Supabase user UUID, and inserts a profile row
     linking the UUID to a fresh username + machine token.
  4. The token in the response is for Angela's iOS Shortcut — the
     Shortcut can't run an OAuth flow, so it keeps using the
     legacy opaque-token auth path.

If the same Supabase user calls this twice (e.g., they reload mid-
signup), the second call hits the unique index on supabase_user_id
and we return 409 — the row already exists, no need to re-create.
"""

import re
import secrets
import string
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app import db
from backend.app.auth import require_supabase_uid
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
def create_profile(
    req: CreateProfileRequest,
    supabase_uid: str = Depends(require_supabase_uid),
) -> ProfileResponse:
    """Write: link the caller's Supabase Auth identity to a new
    profile row, return the username + machine-token + join date.

    Requires a valid Supabase JWT — anonymous signup is not allowed.
    The username uniqueness is enforced at the DB level; collisions
    surface as 409 'username_taken'. If the same supabase_user_id
    already has a profile, that also surfaces as 409 — re-signup
    isn't a thing."""
    if not _USERNAME_RE.match(req.username):
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
                        "INSERT INTO profiles (username, token, supabase_user_id) "
                        "VALUES (:username, :token, :supabase_uid) "
                        "RETURNING username, token, join_date"
                    ),
                    {
                        "username": req.username,
                        "token": token,
                        "supabase_uid": supabase_uid,
                    },
                )
                .mappings()
                .one()
            )
    except IntegrityError as e:
        # Either username collided (expected if taken), the
        # supabase_user_id is already linked (re-signup), or the
        # token collided (1-in-2^128, ignore). All surface as
        # 409 — we don't distinguish to avoid leaking "is this
        # username taken vs is this Supabase user already linked."
        raise AppError(
            409,
            "username_taken",
            "That username is already taken.",
        ) from e

    return ProfileResponse(**dict(row))
