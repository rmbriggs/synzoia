"""Request + response shapes for /api/posts/*.

A post is a feed event: "user X did activity Y at time Z." The actual
payload lives in the type-specific tables (steps, sleep, workouts) —
this schema is the chronological event log.

Per CLAUDE.md: user_id (and username) are resolved server-side from
the Bearer token, never trusted from the request body.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel


PostType = Literal[
    "sleep",
    "steps",
    "workout",
    "steps_milestone",
    "leaderboard_recap",
]

# Subset of PostType that users are allowed to submit via POST /api/posts.
# `steps_milestone` and `leaderboard_recap` are system-only event types —
# they get inserted by `services.steps.detect_and_insert_milestone` and
# the daily-recap cron, never by user-facing requests. Pydantic enforces
# this at the request boundary with a 422 if a client tries to spoof.
UserSubmittablePostType = Literal["sleep", "steps", "workout"]


class CreatePostRequest(BaseModel):
    """Body shape for POST /api/posts. The client sends only the type
    and timestamp — user_id and username come from the token. The type
    must be a user-submittable kind; system-generated types
    (steps_milestone, leaderboard_recap) are rejected here."""

    type: UserSubmittablePostType
    timestamp: datetime


class PostResponse(BaseModel):
    """Single row representation, returned by POST /api/posts and
    embedded in feed list responses."""

    id: int
    user_id: int
    username: str
    type: PostType
    timestamp: datetime
    details: Optional[dict[str, Any]] = None
    body: Optional[str] = None


class FeedResponse(BaseModel):
    """List response for GET /api/posts. Capped at a fixed limit on the
    service side so clients can't accidentally ask for the whole table."""

    posts: list[PostResponse]
