"""Request + response shapes for /api/sleep/*.

Mirrors the steps schema shape (daily / weekly / monthly / summary
× global / per-user) so frontend code can copy-modify the existing
steps UI for sleep with minimal new mental model.

Read endpoints return ready-to-display JSON. Clients should render
the body directly — no client-side aggregation, ranking, or filtering.

The write endpoint (POST /api/sleep) accepts what the iOS Shortcut
pulls from Apple Health: bedtime, wake_time, total asleep duration,
optional per-stage minutes. `user_id` and `night_of` are resolved
server-side (token + CT-date math) and NEVER from the body.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / read response building blocks
# ---------------------------------------------------------------------------


class LeaderboardEntry(BaseModel):
    """One row of a sleep leaderboard. `total` is duration_min summed
    over the leaderboard's date window."""

    rank: int
    username: str
    total: int


class DailyTotal(BaseModel):
    """One day's sleep total in minutes."""

    date: date
    total: int


class SleepPost(BaseModel):
    """Single sleep row as embedded in per-user daily responses.
    Frontend uses this to render the night's detail card."""

    night_of: date
    bedtime: datetime
    wake_time: datetime
    duration_min: int
    rem_minutes: Optional[int] = None
    core_minutes: Optional[int] = None
    deep_minutes: Optional[int] = None
    awake_minutes: Optional[int] = None


# ---------------------------------------------------------------------------
# Global responses
# ---------------------------------------------------------------------------


class GlobalDailyResponse(BaseModel):
    """Everyone's sleep for a single night. Leaderboard is ranked by
    duration_min for that night (longer = higher rank)."""

    date: date
    total_minutes: int
    participating_users: int
    leaderboard: list[LeaderboardEntry]


class GlobalWeeklyResponse(BaseModel):
    """Seven-night window. Leaderboard sums duration_min across the
    week. daily_breakdown has 7 entries, one per night, in order."""

    week_start: date
    week_end: date  # inclusive; week_start + 6 days
    total_minutes: int
    leaderboard: list[LeaderboardEntry]
    daily_breakdown: list[DailyTotal]


class SummaryLeader(BaseModel):
    username: str
    total: int


class BestNightEver(BaseModel):
    """The single-night record. Sleep is naturally capped at ~720
    minutes per night, so this is roughly 'who hit the ceiling.'"""

    date: date
    total: int
    username: str


class GlobalSummaryResponse(BaseModel):
    total_users: int
    total_minutes_all_time: int
    today_leader: Optional[SummaryLeader] = None
    this_week_leader: Optional[SummaryLeader] = None
    best_night_ever: Optional[BestNightEver] = None


# ---------------------------------------------------------------------------
# Per-user responses
# ---------------------------------------------------------------------------


class UserDailyResponse(BaseModel):
    """One user's sleep for a specific night."""

    username: str
    date: date
    total: int                          # duration_min for that night
    rank_today: Optional[int] = None    # null if no row for that night
    post: Optional[SleepPost] = None    # the night's row, or null


class UserWeeklyResponse(BaseModel):
    username: str
    week_start: date
    week_end: date
    weekly_total: int
    rank_this_week: Optional[int] = None
    daily_breakdown: list[DailyTotal]


class UserMonthlyResponse(BaseModel):
    """One user's stats for a single CT calendar month."""

    username: str
    month_start: date
    month_end: date
    monthly_total: int
    rank_this_month: Optional[int] = None
    daily_breakdown: list[DailyTotal]


class UserBestNight(BaseModel):
    date: date
    total: int


class UserSummaryResponse(BaseModel):
    username: str
    join_date: datetime
    total_minutes_all_time: int
    best_night: Optional[UserBestNight] = None
    rank_all_time: Optional[int] = None
    nights_logged: int


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


class IngestSleepRequest(BaseModel):
    """Body shape for POST /api/sleep — the *raw HealthKit samples*
    payload Angela's iOS Shortcut produces.

    Each of `values`, `starts`, `ends`, `types`, `duration` is a single
    newline-joined string. They're index-aligned and must have equal
    length. `timestamp` is the capture moment as ISO-8601 with offset
    (the Shortcut formats Current Date this way), which is how we
    determine the user's local wall clock for the sample timestamps.

    Sessionization, classification, dedup, and metric computation all
    happen server-side — see services/sleep_sessions.py. The client
    sends raw data, the server returns one row per detected session.
    """

    values: str
    starts: str
    ends: str
    types: str
    duration: str
    timestamp: str


class SleepSessionResponse(BaseModel):
    """One row of the response array returned by POST /api/sleep —
    a detected sleep session (overnight OR nap), with its metrics
    and provisional/final status."""

    id: int
    user_id: int
    session_type: str  # 'night' | 'nap'
    status: str        # 'provisional' | 'final'
    review_flag: bool
    sleep_date: date
    onset: datetime
    wake: datetime
    time_in_bed_min: int
    total_asleep_min: int
    awake_min: int
    core_min: int
    deep_min: int
    rem_min: int
    wakeups: int
    efficiency: float
    captured_at: datetime


class IngestSleepResponse(BaseModel):
    """Wrapper so the response shape can grow (e.g., add `discarded`
    metadata) without breaking existing clients."""

    sessions: list[SleepSessionResponse]
