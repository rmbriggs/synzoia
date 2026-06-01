"""HTTP layer for /api/workouts/*.

Two write endpoints share the same dedup logic via
services/workouts.py:
  POST /api/workouts/run       — distance-based workout
  POST /api/workouts/calories  — calorie-burn-based workout

Each takes a window + heart-rate fields. The kind-specific required
field (distance_m or active_calories) is enforced by the request
schema.
"""

from fastapi import APIRouter, Depends, status

from backend.app import db
from backend.app.auth import require_user
from backend.app.errors import AppError
from backend.app.schemas.workouts import (
    CreateCaloriesRequest,
    CreateRunRequest,
    WorkoutResponse,
)
from backend.app.services import workouts as svc

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


# ----- Write: /run --------------------------------------------------------


@router.post(
    "/run",
    status_code=status.HTTP_201_CREATED,
    response_model=WorkoutResponse,
)
def create_run(
    req: CreateRunRequest,
    user_id: int = Depends(require_user),
) -> WorkoutResponse:
    """POST /api/workouts/run — log a distance-based workout
    (run/ride/walk). Smart-matched by overlap so re-posts of the same
    activity update the existing row.

    `user_id` is resolved from the Bearer token (never trusted from
    the body, per CLAUDE.md).
    """
    workout = svc.WorkoutInput(
        workout_kind="run",
        started_at=req.started_at,
        ended_at=req.ended_at,
        distance_m=req.distance_m,
        active_calories=req.active_calories,
        avg_heart_rate=req.avg_heart_rate,
        max_heart_rate=req.max_heart_rate,
    )
    try:
        with db.get_engine().begin() as conn:
            return svc.upsert_workout(conn, user_id=user_id, workout=workout)
    except svc.InvalidWorkoutError as e:
        raise AppError(422, "invalid_workout", str(e)) from e


# ----- Write: /calories ---------------------------------------------------


@router.post(
    "/calories",
    status_code=status.HTTP_201_CREATED,
    response_model=WorkoutResponse,
)
def create_calories(
    req: CreateCaloriesRequest,
    user_id: int = Depends(require_user),
) -> WorkoutResponse:
    """POST /api/workouts/calories — log a calorie-burn workout
    (strength, yoga, HIIT, anything where distance isn't the point).
    Same overlap-dedup as /run.
    """
    workout = svc.WorkoutInput(
        workout_kind="calories",
        started_at=req.started_at,
        ended_at=req.ended_at,
        active_calories=req.active_calories,
        avg_heart_rate=req.avg_heart_rate,
        max_heart_rate=req.max_heart_rate,
    )
    try:
        with db.get_engine().begin() as conn:
            return svc.upsert_workout(conn, user_id=user_id, workout=workout)
    except svc.InvalidWorkoutError as e:
        raise AppError(422, "invalid_workout", str(e)) from e
