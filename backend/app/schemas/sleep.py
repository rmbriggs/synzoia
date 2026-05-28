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


class CreateSleepRequest(BaseModel):
    """Body shape for POST /api/sleep. The iOS Shortcut sends one of
    these every time it syncs Apple Health overnight-sleep data.

    `night_of` is NOT accepted from the client — the service computes
    it from wake_time's CT date minus 1 day. Per CLAUDE.md, identity
    and derived fields come from the server, not the body.
    """

    bedtime: datetime
    wake_time: datetime
    duration_min: int = Field(ge=0, le=1440)
    rem_minutes: Optional[int] = Field(default=None, ge=0)
    core_minutes: Optional[int] = Field(default=None, ge=0)
    deep_minutes: Optional[int] = Field(default=None, ge=0)
    awake_minutes: Optional[int] = Field(default=None, ge=0)


class CreateSleepResponse(BaseModel):
    """Row returned to the client after a successful POST."""

    id: int
    user_id: int
    bedtime: datetime
    wake_time: datetime
    duration_min: int
    rem_minutes: Optional[int] = None
    core_minutes: Optional[int] = None
    deep_minutes: Optional[int] = None
    awake_minutes: Optional[int] = None
    night_of: date
