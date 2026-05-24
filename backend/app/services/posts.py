"""Posts service: feed reads + writes.

Following the pattern in services/steps.py: this module knows nothing
about HTTP. It takes a SQLAlchemy `Connection` + parameters and returns
Pydantic responses (or raises domain exceptions).

Identifiers are never interpolated from request input. SQL is
parameterized via `text()` + bind params.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.schemas.posts import FeedResponse, PostResponse, PostType


# Maximum rows a single feed query returns. The /api/posts endpoint
# pages by `before` timestamp, so this only bounds one page at a time.
DEFAULT_FEED_LIMIT = 50
MAX_FEED_LIMIT = 200


class UserNotFound(Exception):
    """Raised when a username argument doesn't match any profile."""

    def __init__(self, username: str) -> None:
        super().__init__(username)
        self.username = username


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def create_post(
    conn: Connection,
    user_id: int,
    post_type: PostType,
    timestamp: datetime,
) -> PostResponse:
    """Insert one post row on behalf of `user_id`. The username column
    is denormalized — we look it up from `profiles` here so callers
    can't spoof it via the request body."""
    profile = (
        conn.execute(
            text("SELECT username FROM profiles WHERE id = :id"),
            {"id": user_id},
        )
        .mappings()
        .first()
    )
    if profile is None:
        # Token-resolved user_id should always exist; this only fires if
        # the profile was deleted between auth check and insert (race).
        raise UserNotFound(f"user_id={user_id}")

    row = (
        conn.execute(
            text(
                "INSERT INTO posts (user_id, username, type, timestamp) "
                "VALUES (:user_id, :username, :type, :timestamp) "
                "RETURNING id, user_id, username, type, timestamp"
            ),
            {
                "user_id": user_id,
                "username": profile["username"],
                "type": post_type,
                "timestamp": timestamp,
            },
        )
        .mappings()
        .one()
    )
    return PostResponse(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        username=row["username"],
        type=row["type"],
        timestamp=row["timestamp"],
    )


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def _clamp_limit(limit: Optional[int]) -> int:
    if limit is None:
        return DEFAULT_FEED_LIMIT
    return max(1, min(limit, MAX_FEED_LIMIT))


def list_feed(
    conn: Connection,
    limit: Optional[int] = None,
    type_filter: Optional[PostType] = None,
) -> FeedResponse:
    """Return the universal feed: newest posts first. Optional
    `type_filter` narrows to one activity type."""
    capped = _clamp_limit(limit)

    if type_filter is None:
        rows = (
            conn.execute(
                text(
                    "SELECT id, user_id, username, type, timestamp "
                    "FROM posts "
                    "ORDER BY timestamp DESC, id DESC "
                    "LIMIT :limit"
                ),
                {"limit": capped},
            )
            .mappings()
            .all()
        )
    else:
        rows = (
            conn.execute(
                text(
                    "SELECT id, user_id, username, type, timestamp "
                    "FROM posts "
                    "WHERE type = :type "
                    "ORDER BY timestamp DESC, id DESC "
                    "LIMIT :limit"
                ),
                {"type": type_filter, "limit": capped},
            )
            .mappings()
            .all()
        )

    return FeedResponse(
        posts=[
            PostResponse(
                id=int(r["id"]),
                user_id=int(r["user_id"]),
                username=r["username"],
                type=r["type"],
                timestamp=r["timestamp"],
            )
            for r in rows
        ]
    )


def list_user_feed(
    conn: Connection,
    username: str,
    limit: Optional[int] = None,
) -> FeedResponse:
    """Return posts for a specific user, newest first. Raises
    `UserNotFound` if the username doesn't match any profile (so the
    route layer can map it to a 404)."""
    profile = (
        conn.execute(
            text("SELECT id FROM profiles WHERE username = :u"),
            {"u": username},
        )
        .mappings()
        .first()
    )
    if profile is None:
        raise UserNotFound(username)

    capped = _clamp_limit(limit)
    rows = (
        conn.execute(
            text(
                "SELECT id, user_id, username, type, timestamp "
                "FROM posts "
                "WHERE user_id = :uid "
                "ORDER BY timestamp DESC, id DESC "
                "LIMIT :limit"
            ),
            {"uid": int(profile["id"]), "limit": capped},
        )
        .mappings()
        .all()
    )

    return FeedResponse(
        posts=[
            PostResponse(
                id=int(r["id"]),
                user_id=int(r["user_id"]),
                username=r["username"],
                type=r["type"],
                timestamp=r["timestamp"],
            )
            for r in rows
        ]
    )
