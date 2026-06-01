"""Request + response shapes for /api/workouts/*.

Two write endpoints share most of their shape:
- POST /api/workouts/run       — distance-based; distance_m required
- POST /api/workouts/calories  — calorie-burn-based; active_calories
                                  required

Both accept the same window + heart-rate fields. Each endpoint
validates its own required field via a dedicated request model so
the OpenAPI surface is clear and Pydantic does the checking.

Per CLAUDE.md: user_id is resolved from the Bearer token, NEVER from
the request body.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ----- Shared base for windowing + heart rate -----------------------------


class _WorkoutWindowBase(BaseModel):
    """Common fields for both run + calorie workouts."""

    started_at: datetime
    ended_at: datetime
    active_calories: Optional[int] = Field(default=None, ge=0)
    avg_heart_rate: Optional[int] = Field(default=None, ge=30, le=250)
    max_heart_rate: Optional[int] = Field(default=None, ge=30, le=250)


# ----- Request shapes -----------------------------------------------------


class CreateRunRequest(_WorkoutWindowBase):
    """Body for POST /api/workouts/run. `distance_m` is required —
    that's what makes it a 'run'-kind row."""

    distance_m: int = Field(ge=0, le=500_000)  # 500km sanity cap


class CreateCaloriesRequest(_WorkoutWindowBase):
    """Body for POST /api/workouts/calories. `active_calories` is
    required (overrides the optional base field)."""

    active_calories: int = Field(ge=0, le=50_000)  # 50k cal sanity cap


# ----- Response shape -----------------------------------------------------


class WorkoutResponse(BaseModel):
    """A workout row as returned to the client. Includes derived
    `duration_min` so the client doesn't have to recompute it."""

    id: int
    user_id: int
    workout_kind: str
    started_at: datetime
    ended_at: datetime
    duration_min: int
    distance_m: Optional[int] = None
    active_calories: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    captured_at: datetime
