"""Request + response shapes for /api/workouts/*.

Two write endpoints, each accepting an ARRAY (the iOS Shortcut batches
events per Apple Health export):
  POST /api/workouts/run       — {"runs":    [RunEntry, ...]}
  POST /api/workouts/calories  — {"buckets": [CalorieBucketEntry, ...]}

Why arrays: Apple Health exports the active-energy stream as many
hourly buckets per day, and Strava-style splits can produce multiple
run entries for a single workout. Forcing the client to make N
requests would multiply auth round-trips and break the
overlap-merge / proration logic (which has to see all of a batch
together to merge correctly).

Per CLAUDE.md: user_id resolves from the Bearer token, NEVER from
the request body. The request models below intentionally omit it.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ----- Run ingest ---------------------------------------------------------


class RunEntry(BaseModel):
    """A single run event as posted by the Shortcut.

    The server may merge this with adjacent entries (sub-3-min gap)
    and may drop entries whose pace falls outside [4, 13] mph.
    `calories` and `status` are computed server-side from the
    calorie_buckets stream + captured_at vs ended_at — clients can
    not influence them.
    """

    started_at: datetime
    ended_at: datetime
    distance_m: int = Field(ge=0, le=500_000)
    avg_heart_rate: Optional[int] = Field(default=None, ge=30, le=250)
    max_heart_rate: Optional[int] = Field(default=None, ge=30, le=250)

    @model_validator(mode="after")
    def _ended_after_started(self) -> "RunEntry":
        if self.ended_at <= self.started_at:
            raise ValueError("ended_at must be strictly after started_at")
        return self


class IngestRunsRequest(BaseModel):
    """Body for POST /api/workouts/run. The Shortcut posts one batch
    per ingest tick; the server handles merge + pace guard + proration
    on the whole list together."""

    model_config = ConfigDict(extra="forbid")
    runs: List[RunEntry] = Field(min_length=1, max_length=200)


class RunResponse(BaseModel):
    """A run row as returned to the client, post-merge + post-prorate.
    `calories` is null when calories_unavailable is true (no
    overlapping bucket coverage yet — common for runs ingested before
    Apple Health has flushed the active-energy stream for that hour).
    """

    id: int
    user_id: int
    started_at: datetime
    ended_at: datetime
    duration_min: int
    distance_m: int
    pace_mph: float
    calories: Optional[int] = None
    calories_unavailable: bool
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    status: str  # 'provisional' | 'final'
    captured_at: datetime


class IngestRunsResponse(BaseModel):
    """Server's response to a /run ingest. `runs` is what got stored
    after merge + pace guard (may be shorter than the input). `dropped`
    counts entries the pace guard rejected — surfaced so the client
    can warn the user when their watch is reporting garbage paces."""

    runs: List[RunResponse]
    dropped: int = 0
    merged_pairs: int = 0


# ----- Calorie bucket ingest ----------------------------------------------


class CalorieBucketEntry(BaseModel):
    """One hour of the Apple Health active-energy stream. `hour_end`
    is normally exactly 60 min after `hour_start`, but we accept any
    span < 24h to absorb partial first/last buckets at capture
    boundaries."""

    hour_start: datetime
    hour_end: datetime
    kcal: int = Field(ge=0, le=1500)

    @model_validator(mode="after")
    def _end_after_start(self) -> "CalorieBucketEntry":
        if self.hour_end <= self.hour_start:
            raise ValueError("hour_end must be strictly after hour_start")
        return self


class IngestCaloriesRequest(BaseModel):
    """Body for POST /api/workouts/calories. The Shortcut typically
    posts the trailing N hours every tick; existing buckets get
    upserted (same hour_start) and any runs overlapping the new
    bucket times get their calories re-prorated."""

    model_config = ConfigDict(extra="forbid")
    buckets: List[CalorieBucketEntry] = Field(min_length=1, max_length=720)


class CalorieBucketResponse(BaseModel):
    """A stored bucket. Returned so the client can verify what the
    server now has."""

    id: int
    user_id: int
    hour_start: datetime
    hour_end: datetime
    kcal: int
    captured_at: datetime


class IngestCaloriesResponse(BaseModel):
    """Server's response to a /calories ingest. `affected_runs` lists
    run IDs whose calories were re-prorated because the new buckets
    overlapped their window — the client can use these to refresh
    UI without re-fetching the whole list."""

    buckets: List[CalorieBucketResponse]
    affected_runs: List[int] = Field(default_factory=list)
