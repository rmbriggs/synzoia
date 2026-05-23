"""Request + response shapes for /api/steps/*.

Read endpoints return a single, ready-to-display JSON object. Clients
should render the body directly; they should not aggregate, rank, or
filter on their side.

The write endpoint (POST /api/steps) accepts the minimum payload an
iOS Shortcut can build: a timestamp and a step count. `user_id` is
resolved from the Bearer token, never from the body.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    total: int


class DailyTotal(BaseModel):
    date: date
    total: int


class GlobalDailyResponse(BaseModel):
    date: date
    total_steps: int
    participating_users: int
    leaderboard: list[LeaderboardEntry]


class GlobalWeeklyResponse(BaseModel):
    week_start: date
    week_end: date  # inclusive; week_start + 6 days
    total_steps: int
    leaderboard: list[LeaderboardEntry]  # ranked by weekly total
    daily_breakdown: list[DailyTotal]  # 7 entries, one per day, in order


class SummaryLeader(BaseModel):
    username: str
    total: int


class BestDayEver(BaseModel):
    date: date
    total: int
    username: str


class GlobalSummaryResponse(BaseModel):
    total_users: int
    total_steps_all_time: int
    today_leader: Optional[SummaryLeader] = None
    this_week_leader: Optional[SummaryLeader] = None
    best_day_ever: Optional[BestDayEver] = None


class StepPost(BaseModel):
    timestamp: datetime
    total: int


class UserDailyResponse(BaseModel):
    username: str
    date: date
    total: int
    rank_today: Optional[int] = None  # null if user has no posts that day
    posts: list[StepPost]  # all snapshots, oldest first


class UserWeeklyResponse(BaseModel):
    username: str
    week_start: date
    week_end: date
    weekly_total: int
    rank_this_week: Optional[int] = None
    daily_breakdown: list[DailyTotal]


class UserBestDay(BaseModel):
    date: date
    total: int


class UserSummaryResponse(BaseModel):
    username: str
    join_date: datetime
    total_steps_all_time: int
    best_day: Optional[UserBestDay] = None
    rank_all_time: Optional[int] = None
    days_active: int


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


class CreateStepRequest(BaseModel):
    """Body shape for POST /api/steps. The iOS Shortcut sends one of
    these every time it syncs Apple Health step data."""

    timestamp: datetime
    total: int = Field(ge=0)
    # Upper bound is enforced as a sanity outlier in the service layer
    # (OUTLIER_CAP), not at the schema level — we want the row stored
    # so we can see what HealthKit sent, but excluded from aggregations.


class CreateStepResponse(BaseModel):
    """Row returned to the client after a successful POST."""

    id: int
    user_id: int
    timestamp: datetime
    total: int
