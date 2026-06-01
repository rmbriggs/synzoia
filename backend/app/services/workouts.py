"""Workouts service.

Two write paths (run + calories) share the same overlap-dedup logic,
so the work lives in one private function and the route layer chooses
which `workout_kind` to pass.

Per CLAUDE.md:
    - Identifiers (table/column names) never come from request input.
    - SQL is parameterized via `text()` + bind params.
    - user_id is resolved from the Bearer token, NEVER the body.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.schemas.workouts import WorkoutResponse


# Two workouts overlap (and thus dedupe to the same row) if their
# [started_at, ended_at] intervals are within this many minutes of
# touching. Matches the sleep-sessionization OVERLAP_SLOP_MIN.
OVERLAP_SLOP_MIN = 30


@dataclass
class WorkoutInput:
    """Normalized payload — both /run and /calories collapse to this
    before hitting the service. The route layer maps its request
    schema (Pydantic) onto this dataclass."""
    workout_kind: str  # 'run' | 'calories'
    started_at: datetime
    ended_at: datetime
    distance_m: Optional[int] = None
    active_calories: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None


class InvalidWorkoutError(ValueError):
    """Raised when the window/metrics are structurally bad. Route maps
    to 422."""


# ----- Helpers ------------------------------------------------------------


def _aware_to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _coerce_db_dt(raw) -> datetime:
    """SQLite returns TIMESTAMP columns as ISO strings; Postgres as
    datetime. Normalize to naive datetime for downstream use."""
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None) if raw.tzinfo else raw
    return datetime.fromisoformat(str(raw))


def _duration_min(started: datetime, ended: datetime) -> int:
    """Whole minutes between start and end. Rounds down."""
    secs = int((ended - started).total_seconds())
    return max(0, secs // 60)


def _row_to_response(row) -> WorkoutResponse:
    return WorkoutResponse(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        workout_kind=row["workout_kind"],
        started_at=_coerce_db_dt(row["started_at"]),
        ended_at=_coerce_db_dt(row["ended_at"]),
        duration_min=int(row["duration_min"]),
        distance_m=(
            int(row["distance_m"]) if row["distance_m"] is not None else None
        ),
        active_calories=(
            int(row["active_calories"])
            if row["active_calories"] is not None
            else None
        ),
        avg_heart_rate=(
            int(row["avg_heart_rate"])
            if row["avg_heart_rate"] is not None
            else None
        ),
        max_heart_rate=(
            int(row["max_heart_rate"])
            if row["max_heart_rate"] is not None
            else None
        ),
        captured_at=_coerce_db_dt(row["captured_at"]),
    )


# ----- Overlap dedup ------------------------------------------------------


def _find_overlapping(
    conn: Connection, user_id: int, kind: str, started: datetime, ended: datetime
) -> Optional[dict]:
    """Find an existing workout row of the SAME kind whose
    [started_at, ended_at] window overlaps [started, ended] within
    OVERLAP_SLOP_MIN minutes. Different kinds don't dedupe — a run and
    a HIIT session at the same time would be two distinct rows. Same-
    kind concurrent workouts shouldn't happen in real life.

    Returns the most-recently-captured matching row, or None."""
    slop = timedelta(minutes=OVERLAP_SLOP_MIN)
    s_naive = _aware_to_naive_utc(started)
    e_naive = _aware_to_naive_utc(ended)
    row = (
        conn.execute(
            text(
                "SELECT id, user_id, workout_kind, started_at, ended_at, "
                "       duration_min, distance_m, active_calories, "
                "       avg_heart_rate, max_heart_rate, captured_at "
                "FROM workouts "
                "WHERE user_id = :uid "
                "  AND workout_kind = :kind "
                "  AND started_at < :end_plus "
                "  AND ended_at   > :start_minus "
                "ORDER BY captured_at DESC "
                "LIMIT 1"
            ),
            {
                "uid": user_id,
                "kind": kind,
                "end_plus": e_naive + slop,
                "start_minus": s_naive - slop,
            },
        )
        .mappings()
        .first()
    )
    return dict(row) if row is not None else None


# ----- Insert + update ----------------------------------------------------


def _insert_workout(
    conn: Connection, user_id: int, w: WorkoutInput, capture_dt: datetime
) -> dict:
    started_naive = _aware_to_naive_utc(w.started_at)
    ended_naive = _aware_to_naive_utc(w.ended_at)
    captured_naive = _aware_to_naive_utc(capture_dt)
    dur_min = _duration_min(started_naive, ended_naive)
    if dur_min <= 0:
        raise InvalidWorkoutError("ended_at must be strictly after started_at")
    row = (
        conn.execute(
            text(
                "INSERT INTO workouts ("
                "  user_id, workout_kind, started_at, ended_at, duration_min, "
                "  distance_m, active_calories, avg_heart_rate, max_heart_rate, "
                "  captured_at"
                ") VALUES ("
                "  :uid, :kind, :started, :ended, :dur, "
                "  :dist, :cal, :avg_hr, :max_hr, "
                "  :captured"
                ") RETURNING id, user_id, workout_kind, started_at, ended_at, "
                "  duration_min, distance_m, active_calories, "
                "  avg_heart_rate, max_heart_rate, captured_at"
            ),
            {
                "uid": user_id,
                "kind": w.workout_kind,
                "started": started_naive,
                "ended": ended_naive,
                "dur": dur_min,
                "dist": w.distance_m,
                "cal": w.active_calories,
                "avg_hr": w.avg_heart_rate,
                "max_hr": w.max_heart_rate,
                "captured": captured_naive,
            },
        )
        .mappings()
        .one()
    )
    return dict(row)


def _update_workout(
    conn: Connection, row_id: int, w: WorkoutInput, capture_dt: datetime
) -> None:
    started_naive = _aware_to_naive_utc(w.started_at)
    ended_naive = _aware_to_naive_utc(w.ended_at)
    captured_naive = _aware_to_naive_utc(capture_dt)
    dur_min = _duration_min(started_naive, ended_naive)
    if dur_min <= 0:
        raise InvalidWorkoutError("ended_at must be strictly after started_at")
    conn.execute(
        text(
            "UPDATE workouts SET "
            "  started_at = :started, "
            "  ended_at = :ended, "
            "  duration_min = :dur, "
            "  distance_m = :dist, "
            "  active_calories = :cal, "
            "  avg_heart_rate = :avg_hr, "
            "  max_heart_rate = :max_hr, "
            "  captured_at = :captured "
            "WHERE id = :id"
        ),
        {
            "id": row_id,
            "started": started_naive,
            "ended": ended_naive,
            "dur": dur_min,
            "dist": w.distance_m,
            "cal": w.active_calories,
            "avg_hr": w.avg_heart_rate,
            "max_hr": w.max_heart_rate,
            "captured": captured_naive,
        },
    )


# ----- Top-level entry point ----------------------------------------------


def upsert_workout(
    conn: Connection,
    user_id: int,
    workout: WorkoutInput,
    capture_dt: Optional[datetime] = None,
) -> WorkoutResponse:
    """Insert OR merge a workout. Same-kind workouts that overlap the
    incoming window update the existing row (keeping the latest
    ended_at + metrics, refreshing captured_at). Different-kind
    workouts at the same time are independent rows."""
    if capture_dt is None:
        capture_dt = datetime.now(timezone.utc)
    if workout.ended_at <= workout.started_at:
        raise InvalidWorkoutError("ended_at must be strictly after started_at")

    existing = _find_overlapping(
        conn,
        user_id=user_id,
        kind=workout.workout_kind,
        started=workout.started_at,
        ended=workout.ended_at,
    )

    if existing is None:
        row = _insert_workout(conn, user_id, workout, capture_dt)
        return _row_to_response(row)

    # Merge: keep the later ended_at; bump captured_at to the new
    # snapshot's time. If the incoming ended_at is earlier than the
    # existing one (out-of-order delivery), only refresh captured_at.
    existing_ended = _coerce_db_dt(existing["ended_at"])
    incoming_ended = _aware_to_naive_utc(workout.ended_at)
    if incoming_ended > existing_ended:
        _update_workout(conn, int(existing["id"]), workout, capture_dt)
    else:
        conn.execute(
            text(
                "UPDATE workouts SET captured_at = :captured "
                "WHERE id = :id AND captured_at < :captured"
            ),
            {
                "id": int(existing["id"]),
                "captured": _aware_to_naive_utc(capture_dt),
            },
        )

    # Read back the (now-canonical) row so the caller's response
    # reflects the merged state.
    row = (
        conn.execute(
            text(
                "SELECT id, user_id, workout_kind, started_at, ended_at, "
                "       duration_min, distance_m, active_calories, "
                "       avg_heart_rate, max_heart_rate, captured_at "
                "FROM workouts WHERE id = :id"
            ),
            {"id": int(existing["id"])},
        )
        .mappings()
        .one()
    )
    return _row_to_response(row)
