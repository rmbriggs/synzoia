"""Bearer-token authentication — dual mode.

Two distinct clients hit our API and each one needs a different
authentication shape:

  - Web users (browser): sign up + log in via Supabase Auth
    (email/password). The frontend stores Supabase's session and
    sends the signed JWT on every API call. We verify the JWT's
    signature against `SUPABASE_JWT_SECRET`, take the `sub` claim
    (the user's Supabase UUID), and look up the matching profile
    via `profiles.supabase_user_id` (added in migration 0012).
    This is "real auth" per the final-project spec's bronze
    invariant #5 — passwords + cryptographic verification, not a
    string-lookup dressed up to look like auth.

  - iOS Shortcut (Angela's automation): can't easily run an
    OAuth flow inside Apple Shortcuts, so it uses the legacy
    `profiles.token` opaque string as a machine-to-server API
    key. The backend tries JWT verification first; if the token
    isn't a valid JWT (no dots, bad signature, missing claims),
    it falls back to looking the string up in `profiles.token`.

Dual-mode means web users get real auth without breaking Angela's
Shortcut and without forcing a migration of the 5 existing profiles
that pre-date Supabase Auth. Once a person has both a Supabase
account AND a profile (linked via supabase_user_id), either
credential resolves to the same internal `profiles.id`.

Per CLAUDE.md: user_id is resolved from the token, never from the
request body. Failure modes (missing token, bad JWT signature,
unknown opaque token) all collapse to one generic 401 — callers
should not be able to distinguish them and use that as an oracle.
"""

import logging
import os
from typing import Optional

from fastapi import Header, status
from jose import JWTError, jwt
from sqlalchemy import text

from backend.app import db
from backend.app.errors import AppError

logger = logging.getLogger(__name__)


def _unauthenticated() -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED,
        "unauthenticated",
        "Missing or invalid Authorization header. Expected 'Bearer <token>'.",
    )


def _verify_supabase_jwt(token: str) -> Optional[str]:
    """Verify `token` as a Supabase Auth JWT and return its `sub`
    claim (the Supabase user UUID) on success. Returns None on any
    failure — bad signature, expired, wrong audience, or simply not
    a JWT at all (no dots in the string).

    Supabase signs project JWTs with HS256 and a project-specific
    secret (the `SUPABASE_JWT_SECRET` env var). The audience is
    `authenticated` for any signed-in user. We do NOT call out to
    Supabase to validate — the local signature check is the source
    of truth, which keeps the API path stateless + fast."""
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        # Without the secret we can't verify anything; treat every
        # token as "probably not a JWT" so the opaque-token fallback
        # runs. This keeps dev (where the secret is unset) working.
        return None
    if "." not in token:
        # JWTs are <header>.<payload>.<signature>. No dot → can't
        # possibly be a JWT, save the round-trip into jose.
        return None
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
        # Catches bad signature, expired, wrong audience, malformed
        # payload — anything that means "this isn't a token I issued."
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


def _resolve_supabase_uid(conn, supabase_uid: str) -> Optional[int]:
    """Map a verified Supabase user UUID to the matching
    `profiles.id`. Returns None if no profile is linked yet —
    expected only between signup-via-Supabase-Auth and our
    /api/profiles call that creates the linked row."""
    row = (
        conn.execute(
            text(
                "SELECT id FROM profiles "
                "WHERE supabase_user_id = :sid"
            ),
            {"sid": supabase_uid},
        )
        .mappings()
        .first()
    )
    return int(row["id"]) if row else None


def _resolve_opaque_token(conn, token: str) -> Optional[int]:
    """Legacy API-key path for the iOS Shortcut. The token string
    is matched directly against `profiles.token`."""
    row = (
        conn.execute(
            text("SELECT id FROM profiles WHERE token = :token"),
            {"token": token},
        )
        .mappings()
        .first()
    )
    return int(row["id"]) if row else None


def require_user(authorization: Optional[str] = Header(default=None)) -> int:
    """FastAPI dependency. Parses `Authorization: Bearer <token>` and
    returns the matching `profiles.id`. Tries JWT verification first
    (web flow), falls back to opaque-token lookup (iOS Shortcut).

    Raises `AppError(401)` on any missing / malformed / unknown-token
    case — by design, the failure modes are NOT distinguishable to
    the client to prevent the response status from being used as an
    oracle ('is this a valid Supabase JWT vs is it just unknown')."""
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthenticated()
    token = authorization[len("Bearer "):].strip()
    if not token:
        raise _unauthenticated()

    engine = db.get_engine()
    with engine.connect() as conn:
        # Path 1 — JWT. Returns the Supabase UUID if the signature
        # checks out; None if it isn't a JWT we can verify.
        supabase_uid = _verify_supabase_jwt(token)
        if supabase_uid is not None:
            user_id = _resolve_supabase_uid(conn, supabase_uid)
            if user_id is not None:
                return user_id
            # Valid JWT but no linked profile yet. This is the
            # narrow window between Supabase Auth signup and the
            # follow-up POST /api/profiles. The signup endpoint
            # itself is the only place this is OK; everywhere else
            # we treat it as unauthenticated to keep the endpoint's
            # contract simple.

        # Path 2 — opaque token (iOS Shortcut). Tried regardless
        # of whether JWT verification ran, so a long-lived Shortcut
        # token still works even if the project gets a new JWT
        # secret.
        user_id = _resolve_opaque_token(conn, token)
        if user_id is not None:
            return user_id

    raise _unauthenticated()


def require_supabase_uid(
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Variant of `require_user` for the signup endpoint specifically.
    Returns the Supabase user UUID directly (no profile lookup),
    because at signup time the caller's profile DOESN'T EXIST yet
    — that's literally what they're about to create. The /api/profiles
    POST uses this to link the new row to the right Supabase user.

    Raises 401 if the token isn't a valid Supabase JWT (opaque tokens
    can't sign up — they're already-existing users)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthenticated()
    token = authorization[len("Bearer "):].strip()
    if not token:
        raise _unauthenticated()
    supabase_uid = _verify_supabase_jwt(token)
    if supabase_uid is None:
        raise _unauthenticated()
    return supabase_uid
