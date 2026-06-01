"""HTTP layer for /api/workouts/*.

Two write endpoints; both accept arrays so the iOS Shortcut can
batch a single ingest tick into one request:

  POST /api/workouts/run       — distance-based run events
  POST /api/workouts/calories  — hourly active-energy buckets

A /calories ingest will retroactively populate the `calories` field
on any of the user's runs whose window overlaps the new buckets.
Conversely, a /run ingest reads the current bucket state and stores
prorated calories at write time.

Per CLAUDE.md: `user_id` resolves from the Bearer token, never the
body. The schemas omit it; this layer threads it from `require_user`.
"""

from fastapi import APIRouter, Depends, status

from backend.app import db
from backend.app.auth import require_user
from backend.app.errors import AppError
from backend.app.schemas.workouts import (
    IngestCaloriesRequest,
    IngestCaloriesResponse,
    IngestRunsRequest,
    IngestRunsResponse,
)
from backend.app.services import workouts as svc

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


@router.post(
    "/run",
    status_code=status.HTTP_201_CREATED,
    response_model=IngestRunsResponse,
)
def ingest_runs(
    req: IngestRunsRequest,
    user_id: int = Depends(require_user),
) -> IngestRunsResponse:
    """POST /api/workouts/run — store a batch of run events.

    Server-side processing (see services/workouts.py):
      1. Merge contiguous runs (<3 min gap) — Strava-style autopause.
      2. Pace guard: drop entries with mean pace outside [4, 13] mph.
      3. Prorate calories from the existing calorie_buckets stream.
      4. Upsert by (user_id, started_at).

    Returns the stored rows plus `dropped` (pace-guard rejects) and
    `merged_pairs` so the client can surface what was normalized."""
    try:
        with db.get_engine().begin() as conn:
            return svc.ingest_runs(conn, user_id=user_id, entries=req.runs)
    except svc.InvalidWorkoutError as e:
        raise AppError(422, "invalid_workout", str(e)) from e


@router.post(
    "/calories",
    status_code=status.HTTP_201_CREATED,
    response_model=IngestCaloriesResponse,
)
def ingest_calories(
    req: IngestCaloriesRequest,
    user_id: int = Depends(require_user),
) -> IngestCaloriesResponse:
    """POST /api/workouts/calories — store a batch of hourly
    active-energy buckets and re-prorate any overlapping runs.

    Buckets are upserted by (user_id, hour_start) — Apple Health
    revises bucket values intraday, so we keep the latest. After the
    upsert, any of this user's runs whose [started, ended] overlaps
    the new bucket time range gets its calories + calories_unavailable
    re-computed in place. `affected_runs` returns those run IDs so the
    client can refresh them in the UI."""
    try:
        with db.get_engine().begin() as conn:
            return svc.ingest_calorie_buckets(
                conn, user_id=user_id, buckets=req.buckets
            )
    except svc.InvalidWorkoutError as e:
        raise AppError(422, "invalid_workout", str(e)) from e
