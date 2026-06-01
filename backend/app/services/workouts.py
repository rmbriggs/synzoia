"""Workouts service — runs + calorie buckets.

Two ingest paths, with calorie data feeding back into the run rows:

  ingest_runs              ─► merge contiguous → pace guard → prorate
                              calories from existing buckets → upsert.

  ingest_calorie_buckets   ─► upsert each bucket → find all runs that
                              overlap the new bucket time range →
                              re-prorate their calories in place.

The two paths share one proration helper. Whichever side has the data
first (run or calories), the other catches up on its next ingest.

Per CLAUDE.md:
    - Identifiers (table/column names) never come from request input.
    - SQL is parameterized via `text()` + bind params.
    - user_id is resolved from the Bearer token, NEVER the body.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.schemas.workouts import (
    CalorieBucketEntry,
    CalorieBucketResponse,
    IngestCaloriesResponse,
    IngestRunsResponse,
    RunEntry,
    RunResponse,
)


# ----- Tunables -----------------------------------------------------------

# Two consecutive runs whose gap is shorter than this collapse into
# one. Catches Strava's auto-pause behavior (a stoplight pause shows
# up as two adjacent run records on Apple Health).
MERGE_GAP_MAX_SEC = 180  # 3 min

# Pace guard. A "run" with average pace outside this band is either a
# walk, a bike ride misclassified by the watch, or a GPS glitch.
MIN_PACE_MPH = 4.0
MAX_PACE_MPH = 13.0

# A run captured within this window of its own end is marked
# 'provisional'. Used by the UI to render "still finalizing…" and by
# the client to know it's worth re-fetching shortly.
PROVISIONAL_WINDOW_MIN = 30

METERS_PER_MILE = 1609.344


class InvalidWorkoutError(ValueError):
    """Structurally bad input — route maps to 422."""


@dataclass
class _NormalizedRun:
    """A run after merge + pace guard, ready to be prorated + stored."""
    started_at: datetime
    ended_at: datetime
    distance_m: int
    duration_min: int
    pace_mph: float
    avg_heart_rate: Optional[int]
    max_heart_rate: Optional[int]


# ----- Helpers ------------------------------------------------------------


def _aware_to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _coerce_db_dt(raw) -> datetime:
    """SQLite returns TIMESTAMP columns as ISO strings; Postgres as
    datetime. Normalize to naive datetime for downstream arithmetic."""
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None) if raw.tzinfo else raw
    return datetime.fromisoformat(str(raw))


def _duration_min(started: datetime, ended: datetime) -> int:
    secs = int((ended - started).total_seconds())
    return max(0, secs // 60)


def _pace_mph(distance_m: int, duration_min: int) -> float:
    """Average pace over the run. `duration_min` must be > 0."""
    if duration_min <= 0:
        return 0.0
    miles = distance_m / METERS_PER_MILE
    hours = duration_min / 60.0
    return miles / hours


def _status_for(capture_dt: datetime, ended_at: datetime) -> str:
    """'provisional' if captured within PROVISIONAL_WINDOW_MIN of run
    end, else 'final'. Captures the case where the Shortcut posts
    mid-cool-down before Apple Health has flushed all samples."""
    delta = capture_dt - ended_at
    if delta < timedelta(minutes=PROVISIONAL_WINDOW_MIN):
        return "provisional"
    return "final"


# ----- Merge contiguous runs ---------------------------------------------


def _merge_consecutive(
    entries: Sequence[RunEntry],
) -> Tuple[List[RunEntry], int]:
    """Merge runs whose gap (next.started_at − prev.ended_at) is
    shorter than MERGE_GAP_MAX_SEC. Sums distance, takes the union
    window, max-pools heart-rate fields. Returns (merged, pair_count)
    where pair_count is the number of merges performed (an A+B+C
    triple-merge counts as 2).

    Why max-pool HR: average HR over a longer interval is meaningless
    without sample weights we don't have. Max-pool preserves the most
    useful summary stat without making up an average.
    """
    if not entries:
        return [], 0

    sorted_entries = sorted(entries, key=lambda e: e.started_at)
    out: List[RunEntry] = [sorted_entries[0]]
    pairs = 0

    for nxt in sorted_entries[1:]:
        prev = out[-1]
        gap = (nxt.started_at - prev.ended_at).total_seconds()
        if 0 <= gap < MERGE_GAP_MAX_SEC:
            avg_hr = _max_opt(prev.avg_heart_rate, nxt.avg_heart_rate)
            max_hr = _max_opt(prev.max_heart_rate, nxt.max_heart_rate)
            out[-1] = RunEntry(
                started_at=prev.started_at,
                ended_at=nxt.ended_at,
                distance_m=prev.distance_m + nxt.distance_m,
                avg_heart_rate=avg_hr,
                max_heart_rate=max_hr,
            )
            pairs += 1
        else:
            out.append(nxt)

    return out, pairs


def _max_opt(a: Optional[int], b: Optional[int]) -> Optional[int]:
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


# ----- Pace guard ---------------------------------------------------------


def _apply_pace_guard(
    entries: Sequence[RunEntry],
) -> Tuple[List[_NormalizedRun], int]:
    """Drop entries whose mean pace falls outside [MIN, MAX] mph.
    Returns the survivors as _NormalizedRun (with pace + duration
    pre-computed) and the dropped count.

    Why this lives outside Pydantic: the same entry might be valid
    AFTER merging (a 50m sprint + 4km cooldown merge to a sensible run)
    but invalid alone, so the guard has to run post-merge."""
    survivors: List[_NormalizedRun] = []
    dropped = 0
    for e in entries:
        started = _aware_to_naive_utc(e.started_at)
        ended = _aware_to_naive_utc(e.ended_at)
        dur = _duration_min(started, ended)
        if dur <= 0:
            dropped += 1
            continue
        pace = _pace_mph(e.distance_m, dur)
        if pace < MIN_PACE_MPH or pace > MAX_PACE_MPH:
            dropped += 1
            continue
        survivors.append(
            _NormalizedRun(
                started_at=started,
                ended_at=ended,
                distance_m=e.distance_m,
                duration_min=dur,
                pace_mph=round(pace, 2),
                avg_heart_rate=e.avg_heart_rate,
                max_heart_rate=e.max_heart_rate,
            )
        )
    return survivors, dropped


# ----- Proration ----------------------------------------------------------


def _prorate_calories(
    conn: Connection,
    user_id: int,
    started_at: datetime,
    ended_at: datetime,
) -> Tuple[Optional[int], bool]:
    """Sum the calorie_buckets that overlap [started_at, ended_at]
    for this user, prorating each bucket by overlap fraction.

    Returns (calories_or_None, has_overlap). When no bucket overlaps
    the run window at all, returns (None, False) and the caller marks
    the run as calories_unavailable — the watch wasn't streaming
    active-energy when this run happened, OR Apple Health hasn't
    flushed the relevant hour yet."""
    rows = (
        conn.execute(
            text(
                "SELECT hour_start, hour_end, kcal "
                "FROM calorie_buckets "
                "WHERE user_id = :uid "
                "  AND hour_end   > :start "
                "  AND hour_start < :end"
            ),
            {"uid": user_id, "start": started_at, "end": ended_at},
        )
        .mappings()
        .all()
    )

    if not rows:
        return None, False

    total_kcal = 0.0
    for r in rows:
        b_start = _coerce_db_dt(r["hour_start"])
        b_end = _coerce_db_dt(r["hour_end"])
        kcal = int(r["kcal"])
        overlap_start = max(started_at, b_start)
        overlap_end = min(ended_at, b_end)
        overlap_sec = (overlap_end - overlap_start).total_seconds()
        if overlap_sec <= 0:
            continue
        bucket_sec = (b_end - b_start).total_seconds()
        if bucket_sec <= 0:
            continue
        total_kcal += kcal * (overlap_sec / bucket_sec)

    return int(round(total_kcal)), True


# ----- Run upsert ---------------------------------------------------------


def _upsert_run(
    conn: Connection,
    user_id: int,
    run: _NormalizedRun,
    capture_dt: datetime,
) -> dict:
    """Insert or update by (user_id, started_at). Re-runs proration
    against the current calorie_buckets state every time, so a
    re-posted run picks up any buckets that arrived in between."""
    calories, has_overlap = _prorate_calories(
        conn, user_id, run.started_at, run.ended_at
    )
    captured = _aware_to_naive_utc(capture_dt)
    status_val = _status_for(captured, run.ended_at)
    calories_unavailable = not has_overlap

    existing = (
        conn.execute(
            text(
                "SELECT id FROM runs "
                "WHERE user_id = :uid AND started_at = :started"
            ),
            {"uid": user_id, "started": run.started_at},
        )
        .mappings()
        .first()
    )

    if existing is None:
        row = (
            conn.execute(
                text(
                    "INSERT INTO runs ("
                    "  user_id, started_at, ended_at, duration_min, distance_m, "
                    "  pace_mph, calories, calories_unavailable, "
                    "  avg_heart_rate, max_heart_rate, status, captured_at"
                    ") VALUES ("
                    "  :uid, :started, :ended, :dur, :dist, "
                    "  :pace, :cal, :cu, "
                    "  :avg_hr, :max_hr, :status, :captured"
                    ") RETURNING id, user_id, started_at, ended_at, duration_min, "
                    "  distance_m, pace_mph, calories, calories_unavailable, "
                    "  avg_heart_rate, max_heart_rate, status, captured_at"
                ),
                {
                    "uid": user_id,
                    "started": run.started_at,
                    "ended": run.ended_at,
                    "dur": run.duration_min,
                    "dist": run.distance_m,
                    "pace": run.pace_mph,
                    "cal": calories,
                    "cu": calories_unavailable,
                    "avg_hr": run.avg_heart_rate,
                    "max_hr": run.max_heart_rate,
                    "status": status_val,
                    "captured": captured,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)

    conn.execute(
        text(
            "UPDATE runs SET "
            "  ended_at = :ended, "
            "  duration_min = :dur, "
            "  distance_m = :dist, "
            "  pace_mph = :pace, "
            "  calories = :cal, "
            "  calories_unavailable = :cu, "
            "  avg_heart_rate = :avg_hr, "
            "  max_heart_rate = :max_hr, "
            "  status = :status, "
            "  captured_at = :captured "
            "WHERE id = :id"
        ),
        {
            "id": int(existing["id"]),
            "ended": run.ended_at,
            "dur": run.duration_min,
            "dist": run.distance_m,
            "pace": run.pace_mph,
            "cal": calories,
            "cu": calories_unavailable,
            "avg_hr": run.avg_heart_rate,
            "max_hr": run.max_heart_rate,
            "status": status_val,
            "captured": captured,
        },
    )

    row = (
        conn.execute(
            text(
                "SELECT id, user_id, started_at, ended_at, duration_min, "
                "       distance_m, pace_mph, calories, calories_unavailable, "
                "       avg_heart_rate, max_heart_rate, status, captured_at "
                "FROM runs WHERE id = :id"
            ),
            {"id": int(existing["id"])},
        )
        .mappings()
        .one()
    )
    return dict(row)


def _run_row_to_response(row: dict) -> RunResponse:
    return RunResponse(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        started_at=_coerce_db_dt(row["started_at"]),
        ended_at=_coerce_db_dt(row["ended_at"]),
        duration_min=int(row["duration_min"]),
        distance_m=int(row["distance_m"]),
        pace_mph=float(row["pace_mph"]),
        calories=(int(row["calories"]) if row["calories"] is not None else None),
        calories_unavailable=bool(row["calories_unavailable"]),
        avg_heart_rate=(
            int(row["avg_heart_rate"]) if row["avg_heart_rate"] is not None else None
        ),
        max_heart_rate=(
            int(row["max_heart_rate"]) if row["max_heart_rate"] is not None else None
        ),
        status=row["status"],
        captured_at=_coerce_db_dt(row["captured_at"]),
    )


# ----- Calorie bucket upsert ---------------------------------------------


def _upsert_calorie_bucket(
    conn: Connection,
    user_id: int,
    bucket: CalorieBucketEntry,
    capture_dt: datetime,
) -> dict:
    """Insert or update by (user_id, hour_start). Apple Health revises
    bucket values as more samples arrive within the hour, so we keep
    the latest."""
    h_start = _aware_to_naive_utc(bucket.hour_start)
    h_end = _aware_to_naive_utc(bucket.hour_end)
    captured = _aware_to_naive_utc(capture_dt)

    existing = (
        conn.execute(
            text(
                "SELECT id FROM calorie_buckets "
                "WHERE user_id = :uid AND hour_start = :hs"
            ),
            {"uid": user_id, "hs": h_start},
        )
        .mappings()
        .first()
    )

    if existing is None:
        row = (
            conn.execute(
                text(
                    "INSERT INTO calorie_buckets ("
                    "  user_id, hour_start, hour_end, kcal, captured_at"
                    ") VALUES (:uid, :hs, :he, :kcal, :captured) "
                    "RETURNING id, user_id, hour_start, hour_end, kcal, captured_at"
                ),
                {
                    "uid": user_id,
                    "hs": h_start,
                    "he": h_end,
                    "kcal": bucket.kcal,
                    "captured": captured,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)

    conn.execute(
        text(
            "UPDATE calorie_buckets SET "
            "  hour_end = :he, "
            "  kcal = :kcal, "
            "  captured_at = :captured "
            "WHERE id = :id"
        ),
        {
            "id": int(existing["id"]),
            "he": h_end,
            "kcal": bucket.kcal,
            "captured": captured,
        },
    )

    row = (
        conn.execute(
            text(
                "SELECT id, user_id, hour_start, hour_end, kcal, captured_at "
                "FROM calorie_buckets WHERE id = :id"
            ),
            {"id": int(existing["id"])},
        )
        .mappings()
        .one()
    )
    return dict(row)


def _bucket_row_to_response(row: dict) -> CalorieBucketResponse:
    return CalorieBucketResponse(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        hour_start=_coerce_db_dt(row["hour_start"]),
        hour_end=_coerce_db_dt(row["hour_end"]),
        kcal=int(row["kcal"]),
        captured_at=_coerce_db_dt(row["captured_at"]),
    )


def _reprorate_overlapping_runs(
    conn: Connection,
    user_id: int,
    range_start: datetime,
    range_end: datetime,
    capture_dt: datetime,
) -> List[int]:
    """After ingesting new buckets, find this user's runs that overlap
    [range_start, range_end] and re-run proration on them. Returns the
    list of affected run IDs.

    Note: we DO NOT touch the run's status here. status is governed by
    captured_at vs ended_at on the run; a calorie bucket landing
    afterwards doesn't change when the run was captured."""
    runs = (
        conn.execute(
            text(
                "SELECT id, started_at, ended_at FROM runs "
                "WHERE user_id = :uid "
                "  AND started_at < :end "
                "  AND ended_at   > :start"
            ),
            {"uid": user_id, "start": range_start, "end": range_end},
        )
        .mappings()
        .all()
    )

    affected: List[int] = []
    for r in runs:
        rid = int(r["id"])
        r_start = _coerce_db_dt(r["started_at"])
        r_end = _coerce_db_dt(r["ended_at"])
        calories, has_overlap = _prorate_calories(conn, user_id, r_start, r_end)
        conn.execute(
            text(
                "UPDATE runs SET "
                "  calories = :cal, "
                "  calories_unavailable = :cu "
                "WHERE id = :id"
            ),
            {
                "id": rid,
                "cal": calories,
                "cu": not has_overlap,
            },
        )
        affected.append(rid)
    return affected


# ----- Public entry points ------------------------------------------------


def ingest_runs(
    conn: Connection,
    user_id: int,
    entries: Sequence[RunEntry],
    capture_dt: Optional[datetime] = None,
) -> IngestRunsResponse:
    """Merge → pace guard → prorate → upsert. Returns what was stored
    plus counters the client can surface to the user."""
    if capture_dt is None:
        capture_dt = datetime.now(timezone.utc)
    if not entries:
        raise InvalidWorkoutError("runs list is empty")

    merged, merged_pairs = _merge_consecutive(list(entries))
    survivors, dropped = _apply_pace_guard(merged)

    stored: List[RunResponse] = []
    for run in survivors:
        row = _upsert_run(conn, user_id, run, capture_dt)
        stored.append(_run_row_to_response(row))

    return IngestRunsResponse(
        runs=stored,
        dropped=dropped,
        merged_pairs=merged_pairs,
    )


def ingest_calorie_buckets(
    conn: Connection,
    user_id: int,
    buckets: Sequence[CalorieBucketEntry],
    capture_dt: Optional[datetime] = None,
) -> IngestCaloriesResponse:
    """Upsert each bucket, then re-prorate any of this user's runs
    whose window overlaps the new bucket range."""
    if capture_dt is None:
        capture_dt = datetime.now(timezone.utc)
    if not buckets:
        raise InvalidWorkoutError("buckets list is empty")

    stored: List[CalorieBucketResponse] = []
    range_start = min(_aware_to_naive_utc(b.hour_start) for b in buckets)
    range_end = max(_aware_to_naive_utc(b.hour_end) for b in buckets)

    for b in buckets:
        row = _upsert_calorie_bucket(conn, user_id, b, capture_dt)
        stored.append(_bucket_row_to_response(row))

    affected = _reprorate_overlapping_runs(
        conn, user_id, range_start, range_end, capture_dt
    )

    return IngestCaloriesResponse(buckets=stored, affected_runs=affected)
