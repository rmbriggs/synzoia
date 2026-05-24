"""HTTP layer for /api/posts/*.

Thin: parse params, open a connection, dispatch to the service, return
the response. All filtering / clamping / lookups live in
`backend.app.services.posts` so it stays testable as plain functions.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from backend.app import db
from backend.app.auth import require_user
from backend.app.errors import AppError
from backend.app.schemas.posts import (
    CreatePostRequest,
    FeedResponse,
    PostResponse,
    PostType,
)
from backend.app.services import posts as svc

router = APIRouter(prefix="/api/posts", tags=["posts"])


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


@router.get("", response_model=FeedResponse)
def list_feed(
    limit: Optional[int] = Query(default=None, ge=1, le=svc.MAX_FEED_LIMIT),
    type: Optional[PostType] = Query(default=None),
) -> FeedResponse:
    """Universal feed: all posts, newest first. `type` filters to one
    activity kind ('sleep', 'steps', or 'workout')."""
    with db.get_engine().connect() as conn:
        return svc.list_feed(conn, limit=limit, type_filter=type)


@router.get(
    "/users/{username}",
    response_model=FeedResponse,
)
def list_user_feed(
    username: str,
    limit: Optional[int] = Query(default=None, ge=1, le=svc.MAX_FEED_LIMIT),
) -> FeedResponse:
    """One user's posts, newest first. 404 if the username doesn't exist."""
    try:
        with db.get_engine().connect() as conn:
            return svc.list_user_feed(conn, username=username, limit=limit)
    except svc.UserNotFound as e:
        raise AppError(
            404,
            "user_not_found",
            f"No user named {e.username!r}.",
        ) from e


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PostResponse,
)
def create_post(
    req: CreatePostRequest,
    user_id: int = Depends(require_user),
) -> PostResponse:
    """POST /api/posts — log a feed event. The iOS Shortcut (or any
    other writer) hits this whenever an activity should appear in the
    universal feed. `user_id` and `username` are resolved server-side
    from the Bearer token — never trusted from the request body."""
    try:
        with db.get_engine().begin() as conn:
            return svc.create_post(
                conn,
                user_id=user_id,
                post_type=req.type,
                timestamp=req.timestamp,
            )
    except svc.UserNotFound:
        # Token resolved a user_id that no longer exists. Race condition;
        # treat as a fresh 401 so the client knows to re-authenticate.
        raise AppError(
            401,
            "unauthenticated",
            "Token refers to a profile that no longer exists.",
        )
