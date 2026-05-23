"""Step aggregation service.

Responsibilities (per CLAUDE.md):
- Fetch raw step data from Supabase via SQLAlchemy.
- Clean (outlier cap; null safety) and aggregate (MAX-per-day, SUM-per-week,
  ranking) on the server.
- Return ready-to-display response objects to the route layer.

The route layer talks HTTP. This module knows nothing about HTTP — it
takes a `Connection` + parameters, returns Pydantic responses (or raises
`UserNotFound`).

SQL is parameterized via `text()` + bind params. Identifiers are never
interpolated from request input. Queries use only the SQLite-compatible
subset (`DATE()`, plain GROUP BY, no `RANK() OVER`) so the test suite can
run against in-memory SQLite the same way the rest of the backend does.
Ranking is computed in Python after fetching ordered rows.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

from backend.app.schemas.steps import (
    BestDayEver,
    CreateStepResponse,
    DailyTotal,
    GlobalDailyResponse,
    GlobalSummaryResponse,
    GlobalWeeklyResponse,
    LeaderboardEntry,
    StepPost,
    SummaryLeader,
    UserBestDay,
    UserDailyResponse,
    UserSummaryResponse,
    UserWeeklyResponse,
)

# Daily step counts above this are treated as data errors and dropped.
# 200_000 ≈ 100 miles walked in a day — well past any realistic human
# day, comfortably above any monotonic-counter glitch we've actually
# seen out of HealthKit in testing.
OUTLIER_CAP = 200_000


class UserNotFound(Exception):
    """Raised by per-user services when the username doesn't exist."""

    def __init__(self, username: str) -> None:
        super().__init__(username)
        self.username = username


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iso_week_bounds(week_start: date) -> tuple[date, date]:
    """Return (week_start, week_end_inclusive). Caller picks Monday."""
    return week_start, week_start + timedelta(days=6)


def _lookup_user(conn: Connection, username: str) -> tuple[int, datetime]:
    row = (
        conn.execute(
            text("SELECT id, join_date FROM profiles WHERE username = :u"),
            {"u": username},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise UserNotFound(username)
    return int(row["id"]), row["join_date"]


def _usernames_for(conn: Connection, user_ids: Iterable[int]) -> dict[int, str]:
    ids = list({int(i) for i in user_ids})
    if not ids:
        return {}
    stmt = text(
        "SELECT id, username FROM profiles WHERE id IN :ids"
    ).bindparams(bindparam("ids", expanding=True))
    rows = conn.execute(stmt, {"ids": ids}).mappings().all()
    return {int(r["id"]): r["username"] for r in rows}


def _daily_totals_in_range(
    conn: Connection, start_date: date, end_date: date
) -> list[tuple[int, date, int]]:
    """All (user_id, day, MAX(total)) tuples in [start_date, end_date].
    Outlier rows (total > OUTLIER_CAP) are filtered BEFORE aggregation,
    so a single bad row can't poison a user's daily total."""
    rows = (
        conn.execute(
            text(
                "SELECT user_id, DATE(timestamp) AS d, MAX(total) AS daily_total "
                "FROM steps "
                "WHERE DATE(timestamp) >= :start "
                "AND DATE(timestamp) <= :end "
                "AND total <= :cap "
                "GROUP BY user_id, DATE(timestamp)"
            ),
            {"start": start_date, "end": end_date, "cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )
    out: list[tuple[int, date, int]] = []
    for r in rows:
        d = r["d"]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        out.append((int(r["user_id"]), d, int(r["daily_total"])))
    return out


def _build_leaderboard(
    totals_by_user: dict[int, int],
    usernames: dict[int, str],
) -> list[LeaderboardEntry]:
    """Order by total desc, then username asc for stability. Dense
    rank: ties share a rank, the next distinct total uses rank+1."""
    items = sorted(
        ((uid, t) for uid, t in totals_by_user.items() if uid in usernames),
        key=lambda x: (-x[1], usernames[x[0]]),
    )
    out: list[LeaderboardEntry] = []
    rank = 0
    last_total: int | None = None
    for uid, total in items:
        if total != last_total:
            rank += 1
            last_total = total
        out.append(
            LeaderboardEntry(rank=rank, username=usernames[uid], total=total)
        )
    return out


def _rank_of_user(
    totals_by_user: dict[int, int], target_user_id: int
) -> int | None:
    """Dense rank of a user inside totals_by_user, or None if absent."""
    if target_user_id not in totals_by_user:
        return None
    target_total = totals_by_user[target_user_id]
    distinct_above = {
        t for uid, t in totals_by_user.items() if t > target_total
    }
    return len(distinct_above) + 1


# ---------------------------------------------------------------------------
# Global endpoints
# ---------------------------------------------------------------------------


def get_global_daily(conn: Connection, target_date: date) -> GlobalDailyResponse:
    rows = _daily_totals_in_range(conn, target_date, target_date)
    totals_by_user = {uid: total for uid, _d, total in rows}
    usernames = _usernames_for(conn, totals_by_user.keys())
    leaderboard = _build_leaderboard(totals_by_user, usernames)
    return GlobalDailyResponse(
        date=target_date,
        total_steps=sum(totals_by_user.values()),
        participating_users=len(totals_by_user),
        leaderboard=leaderboard,
    )


def get_global_weekly(
    conn: Connection, week_start: date
) -> GlobalWeeklyResponse:
    start, end = _iso_week_bounds(week_start)
    rows = _daily_totals_in_range(conn, start, end)

    weekly_totals: dict[int, int] = defaultdict(int)
    daily_global: dict[date, int] = defaultdict(int)
    for uid, d, total in rows:
        weekly_totals[uid] += total
        daily_global[d] += total

    usernames = _usernames_for(conn, weekly_totals.keys())
    leaderboard = _build_leaderboard(weekly_totals, usernames)

    # Fill in zero-step days so the array is always 7 entries.
    daily_breakdown = [
        DailyTotal(
            date=start + timedelta(days=offset),
            total=daily_global.get(start + timedelta(days=offset), 0),
        )
        for offset in range(7)
    ]

    return GlobalWeeklyResponse(
        week_start=start,
        week_end=end,
        total_steps=sum(weekly_totals.values()),
        leaderboard=leaderboard,
        daily_breakdown=daily_breakdown,
    )


def get_global_summary(
    conn: Connection, today: date, week_start: date
) -> GlobalSummaryResponse:
    total_users = int(
        conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar() or 0
    )

    # All-time aggregates: walk every (user, day) MAX once.
    all_daily = (
        conn.execute(
            text(
                "SELECT user_id, DATE(timestamp) AS d, MAX(total) AS daily_total "
                "FROM steps "
                "WHERE total <= :cap "
                "GROUP BY user_id, DATE(timestamp)"
            ),
            {"cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )
    total_steps_all_time = sum(int(r["daily_total"]) for r in all_daily)

    # Best day ever: row with the highest daily_total across all users/days.
    best_row = max(
        all_daily,
        key=lambda r: int(r["daily_total"]),
        default=None,
    )
    best_day_ever: BestDayEver | None = None
    if best_row is not None:
        best_uid = int(best_row["user_id"])
        usernames = _usernames_for(conn, [best_uid])
        if best_uid in usernames:
            d = best_row["d"]
            if isinstance(d, str):
                d = date.fromisoformat(d)
            best_day_ever = BestDayEver(
                date=d,
                total=int(best_row["daily_total"]),
                username=usernames[best_uid],
            )

    today_leader = _top_leader(conn, today, today)
    week_end = week_start + timedelta(days=6)
    this_week_leader = _top_leader(conn, week_start, week_end)

    return GlobalSummaryResponse(
        total_users=total_users,
        total_steps_all_time=total_steps_all_time,
        today_leader=today_leader,
        this_week_leader=this_week_leader,
        best_day_ever=best_day_ever,
    )


def _top_leader(
    conn: Connection, start_date: date, end_date: date
) -> SummaryLeader | None:
    """Single highest scorer over [start_date, end_date], summed across
    the range. Used by /api/steps/summary for today and this-week."""
    rows = _daily_totals_in_range(conn, start_date, end_date)
    if not rows:
        return None
    totals: dict[int, int] = defaultdict(int)
    for uid, _d, total in rows:
        totals[uid] += total
    usernames = _usernames_for(conn, totals.keys())
    visible = [(uid, t) for uid, t in totals.items() if uid in usernames]
    if not visible:
        return None
    visible.sort(key=lambda x: (-x[1], usernames[x[0]]))
    top_uid, top_total = visible[0]
    return SummaryLeader(username=usernames[top_uid], total=top_total)


# ---------------------------------------------------------------------------
# Per-user endpoints
# ---------------------------------------------------------------------------


def get_user_daily(
    conn: Connection, username: str, target_date: date
) -> UserDailyResponse:
    user_id, _join_date = _lookup_user(conn, username)

    rows = _daily_totals_in_range(conn, target_date, target_date)
    totals_by_user = {uid: total for uid, _d, total in rows}
    rank = _rank_of_user(totals_by_user, user_id)
    user_total = totals_by_user.get(user_id, 0)

    # Pull the raw posts for that day so the UI can sparkline them.
    post_rows = (
        conn.execute(
            text(
                "SELECT timestamp, total FROM steps "
                "WHERE user_id = :uid "
                "AND DATE(timestamp) = :d "
                "AND total <= :cap "
                "ORDER BY timestamp ASC, id ASC"
            ),
            {"uid": user_id, "d": target_date, "cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )
    posts = [
        StepPost(timestamp=r["timestamp"], total=int(r["total"]))
        for r in post_rows
    ]

    return UserDailyResponse(
        username=username,
        date=target_date,
        total=user_total,
        rank_today=rank,
        posts=posts,
    )


def get_user_weekly(
    conn: Connection, username: str, week_start: date
) -> UserWeeklyResponse:
    user_id, _join_date = _lookup_user(conn, username)
    start, end = _iso_week_bounds(week_start)
    rows = _daily_totals_in_range(conn, start, end)

    weekly_totals: dict[int, int] = defaultdict(int)
    user_daily: dict[date, int] = {}
    for uid, d, total in rows:
        weekly_totals[uid] += total
        if uid == user_id:
            user_daily[d] = total

    rank = _rank_of_user(weekly_totals, user_id)

    daily_breakdown = [
        DailyTotal(
            date=start + timedelta(days=offset),
            total=user_daily.get(start + timedelta(days=offset), 0),
        )
        for offset in range(7)
    ]

    return UserWeeklyResponse(
        username=username,
        week_start=start,
        week_end=end,
        weekly_total=weekly_totals.get(user_id, 0),
        rank_this_week=rank,
        daily_breakdown=daily_breakdown,
    )


def get_user_summary(
    conn: Connection, username: str
) -> UserSummaryResponse:
    user_id, join_date = _lookup_user(conn, username)

    # All (user, day) aggregates once.
    rows = (
        conn.execute(
            text(
                "SELECT user_id, DATE(timestamp) AS d, MAX(total) AS daily_total "
                "FROM steps "
                "WHERE total <= :cap "
                "GROUP BY user_id, DATE(timestamp)"
            ),
            {"cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )

    totals_by_user: dict[int, int] = defaultdict(int)
    user_days: list[tuple[date, int]] = []
    for r in rows:
        uid = int(r["user_id"])
        d_raw = r["d"]
        d = date.fromisoformat(d_raw) if isinstance(d_raw, str) else d_raw
        daily_total = int(r["daily_total"])
        totals_by_user[uid] += daily_total
        if uid == user_id:
            user_days.append((d, daily_total))

    rank_all_time = _rank_of_user(totals_by_user, user_id)

    best_day: UserBestDay | None = None
    if user_days:
        best_d, best_t = max(user_days, key=lambda x: x[1])
        best_day = UserBestDay(date=best_d, total=best_t)

    return UserSummaryResponse(
        username=username,
        join_date=join_date,
        total_steps_all_time=totals_by_user.get(user_id, 0),
        best_day=best_day,
        rank_all_time=rank_all_time,
        days_active=len(user_days),
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def create_step(
    conn: Connection,
    user_id: int,
    timestamp: datetime,
    total: int,
) -> CreateStepResponse:
    """Insert one step row on behalf of `user_id`. The caller is
    responsible for resolving `user_id` from the Bearer token before
    invoking this — this layer does NOT look at HTTP headers."""
    row = (
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) "
                "VALUES (:user_id, :timestamp, :total) "
                "RETURNING id, user_id, timestamp, total"
            ),
            {"user_id": user_id, "timestamp": timestamp, "total": total},
        )
        .mappings()
        .one()
    )
    return CreateStepResponse(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        timestamp=row["timestamp"],
        total=int(row["total"]),
    )
