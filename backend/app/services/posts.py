"""Posts service: feed reads + writes.

Following the pattern in services/steps.py: this module knows nothing
about HTTP. It takes a SQLAlchemy `Connection` + parameters and returns
Pydantic responses (or raises domain exceptions).

Identifiers are never interpolated from request input. SQL is
parameterized via `text()` + bind params.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

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
                "RETURNING id, user_id, username, type, timestamp, details, body"
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
        details=_parse_details(row["details"]),
        body=row["body"],
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
                    "SELECT id, user_id, username, type, timestamp, details, body "
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
                    "SELECT id, user_id, username, type, timestamp, details, body "
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
                details=_parse_details(r["details"]),
                body=r["body"],
            )
            for r in rows
        ]
    )


def _parse_details(raw: Any) -> Optional[dict]:
    """The `details` column is jsonb in Postgres but text in the SQLite
    test backend. Normalize to a dict (or None) before constructing
    PostResponse."""
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) else None
    if isinstance(raw, dict):
        return raw
    return None


def _recap_mentions(details: Any, target_username: str) -> bool:
    """True iff `details.top` is a list containing an entry whose
    username equals `target_username`."""
    parsed = _parse_details(details)
    if parsed is None:
        return False
    top = parsed.get("top")
    if not isinstance(top, list):
        return False
    return any(
        isinstance(entry, dict) and entry.get("username") == target_username
        for entry in top
    )


def list_user_feed(
    conn: Connection,
    username: str,
    limit: Optional[int] = None,
) -> FeedResponse:
    """Return posts that mention `username`: the union of (a) posts
    whose user_id matches and (b) leaderboard_recap posts whose
    `details.top` list contains the username. Sorted newest-first,
    deduped by id, clamped to `limit` (default DEFAULT_FEED_LIMIT,
    max MAX_FEED_LIMIT). Raises `UserNotFound` if the username
    doesn't match any profile (so the route layer can map it to 404)."""
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
    user_id = int(profile["id"])

    authored_rows = (
        conn.execute(
            text(
                "SELECT id, user_id, username, type, timestamp, details, body "
                "FROM posts "
                "WHERE user_id = :uid "
                "ORDER BY timestamp DESC, id DESC "
                "LIMIT :limit"
            ),
            {"uid": user_id, "limit": capped},
        )
        .mappings()
        .all()
    )

    # Recap mentions: pull all leaderboard_recap rows, filter in Python
    # since `details` is jsonb in Postgres but text in the SQLite test
    # backend — we keep parsing portable rather than dialect-specific.
    # Recap row count is bounded by app age in days (one cron per day), so
    # scanning unbounded is fine for v1. Revisit if recap cadence increases.
    recap_rows = (
        conn.execute(
            text(
                "SELECT id, user_id, username, type, timestamp, details, body "
                "FROM posts "
                "WHERE type = 'leaderboard_recap' "
                "ORDER BY timestamp DESC, id DESC"
            )
        )
        .mappings()
        .all()
    )
    mentioning = [
        r for r in recap_rows if _recap_mentions(r["details"], username)
    ]

    # Merge authored + recap-mention rows, dedup by id (a recap authored
    # by the target that ALSO mentions them must appear exactly once).
    by_id: dict[int, dict] = {}
    for r in authored_rows:
        by_id[int(r["id"])] = dict(r)
    for r in mentioning:
        by_id.setdefault(int(r["id"]), dict(r))

    merged = sorted(
        by_id.values(),
        key=lambda r: (r["timestamp"], r["id"]),
        reverse=True,
    )[:capped]

    return FeedResponse(
        posts=[
            PostResponse(
                id=int(r["id"]),
                user_id=int(r["user_id"]),
                username=r["username"],
                type=r["type"],
                timestamp=r["timestamp"],
                details=_parse_details(r["details"]),
                body=r["body"],
            )
            for r in merged
        ]
    )
