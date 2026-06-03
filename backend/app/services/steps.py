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

import json as _json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from backend.app.services.windows import cap_and_sum, rolling_bounds
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

# Per-day cap used by the 30-day global ranking. Each user's daily total
# is capped at this value before summing so a single exceptional day
# can't carry a user's entire leaderboard position.
STEPS_DAILY_CAP = 20_000

# Step counts at which the feed celebrates the user's day. Per-day,
# per-user, per-threshold idempotent — once crossed today, the same
# threshold won't fire again until tomorrow CT.
MILESTONE_THRESHOLDS = (1000, 5000, 10000)

# synzoia displays in Central Time. The iOS Shortcut writes step
# timestamps as UTC (the `ISO 8601` formatter in Shortcuts produces
# the `Z` form, which psycopg strips to a naive UTC value when
# inserting into the `timestamp without time zone` column). So every
# row's stored value is effectively UTC.
#
# To bucket by the date a user actually walked (CT, not UTC), we
# interpret the stored naive value as UTC, convert to CT, and take
# the date there. Doing the conversion in Python keeps the SQL
# portable across Postgres + SQLite (the test backend).
APP_TZ = ZoneInfo("America/Chicago")


def _ct_date(ts) -> date:
    """Convert a stored-as-UTC timestamp (str from SQLite, datetime
    from Postgres; naive or aware) to its calendar date in CT."""
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(APP_TZ).date()


def _utc_window(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """UTC datetime window guaranteed to cover the CT-date range
    [start_date, end_date] inclusive. Pads by one day on each side
    so timestamps that cross the CT/UTC boundary aren't missed."""
    lower = datetime.combine(start_date - timedelta(days=1), datetime.min.time())
    upper = datetime.combine(end_date + timedelta(days=2), datetime.min.time())
    return lower, upper


class UserNotFound(Exception):
    """Raised by per-user services when the username doesn't exist."""

    def __init__(self, username: str) -> None:
        super().__init__(username)
        self.username = username


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _lookup_user(conn: Connection, username: str) -> tuple[int, datetime]:
    row = (
        conn.execute(
            text("SELECT id, join_date FROM profiles WHERE lower(username) = :u"),
            {"u": username.lower()},
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
    """All (user_id, day, MAX(total)) tuples whose CT date falls in
    [start_date, end_date]. Pulls a UTC-widened window of rows and
    buckets in Python so timestamps stored as UTC bucket to the date
    the user actually walked (their CT wall clock), not the date the
    naive value happens to print as.

    Outlier rows (total > OUTLIER_CAP) are filtered BEFORE aggregation,
    so a single bad row can't poison a user's daily total."""
    lower, upper = _utc_window(start_date, end_date)
    rows = (
        conn.execute(
            text(
                "SELECT user_id, timestamp, total FROM steps "
                "WHERE timestamp >= :lower AND timestamp < :upper "
                "AND total <= :cap"
            ),
            {"lower": lower, "upper": upper, "cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )
    by_bucket: dict[tuple[int, date], int] = {}
    for r in rows:
        d = _ct_date(r["timestamp"])
        if d < start_date or d > end_date:
            continue
        key = (int(r["user_id"]), d)
        total = int(r["total"])
        if total > by_bucket.get(key, -1):
            by_bucket[key] = total
    return [(uid, day, total) for (uid, day), total in by_bucket.items()]


def _all_time_daily_max(
    conn: Connection,
) -> dict[tuple[int, date], int]:
    """Per (user_id, CT-day) MAX(total) across the entire steps table.

    Single source of truth for the all-time aggregation — every callsite
    that wants 'a user's all-time total' or 'every user's all-time total'
    builds on this. Outlier rows (total > OUTLIER_CAP) are filtered
    before bucketing, matching the per-CT-day aggregator used elsewhere."""
    rows = (
        conn.execute(
            text(
                "SELECT user_id, timestamp, total FROM steps "
                "WHERE total <= :cap"
            ),
            {"cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )
    daily_max: dict[tuple[int, date], int] = {}
    for r in rows:
        d = _ct_date(r["timestamp"])
        key = (int(r["user_id"]), d)
        t = int(r["total"])
        if t > daily_max.get(key, -1):
            daily_max[key] = t
    return daily_max


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
    conn: Connection, as_of: date
) -> GlobalWeeklyResponse:
    start, end = rolling_bounds(as_of, 7)
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


def get_global_ranking(conn: Connection, as_of: date) -> GlobalWeeklyResponse:
    """Global board ranked by the 30-day capped score (per-CT-day totals,
    each capped at STEPS_DAILY_CAP, summed over [as_of-29, as_of])."""
    start, end = rolling_bounds(as_of, 30)
    rows = _daily_totals_in_range(conn, start, end)
    scores = cap_and_sum(rows, STEPS_DAILY_CAP)
    usernames = _usernames_for(conn, scores.keys())
    leaderboard = _build_leaderboard(scores, usernames)
    return GlobalWeeklyResponse(
        week_start=start,
        week_end=end,
        total_steps=sum(scores.values()),
        leaderboard=leaderboard,
        daily_breakdown=[],
    )


def get_global_summary(
    conn: Connection, as_of: date
) -> GlobalSummaryResponse:
    total_users = int(
        conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar() or 0
    )

    # All-time aggregates: walk every row, bucket by (user, CT day).
    daily_max = _all_time_daily_max(conn)
    total_steps_all_time = sum(daily_max.values())

    # Best day ever: highest (user, CT-day) across the table.
    best_day_ever: BestDayEver | None = None
    if daily_max:
        (best_uid, best_d), best_total = max(daily_max.items(), key=lambda kv: kv[1])
        usernames = _usernames_for(conn, [best_uid])
        if best_uid in usernames:
            best_day_ever = BestDayEver(
                date=best_d,
                total=best_total,
                username=usernames[best_uid],
            )

    today_leader = _top_leader(conn, as_of, as_of)
    week_start, week_end = rolling_bounds(as_of, 7)
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
    # UTC window + Python-side CT-date filter for the same reason as
    # _daily_totals_in_range.
    lower, upper = _utc_window(target_date, target_date)
    post_rows = (
        conn.execute(
            text(
                "SELECT timestamp, total FROM steps "
                "WHERE user_id = :uid "
                "AND timestamp >= :lower AND timestamp < :upper "
                "AND total <= :cap "
                "ORDER BY timestamp ASC, id ASC"
            ),
            {
                "uid": user_id,
                "lower": lower,
                "upper": upper,
                "cap": OUTLIER_CAP,
            },
        )
        .mappings()
        .all()
    )
    posts = [
        StepPost(timestamp=r["timestamp"], total=int(r["total"]))
        for r in post_rows
        if _ct_date(r["timestamp"]) == target_date
    ]

    return UserDailyResponse(
        username=username,
        date=target_date,
        total=user_total,
        rank_today=rank,
        posts=posts,
    )


def get_user_weekly(
    conn: Connection, username: str, as_of: date
) -> UserWeeklyResponse:
    user_id, _join_date = _lookup_user(conn, username)
    start, end = rolling_bounds(as_of, 7)
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


def get_user_monthly(
    conn: Connection, username: str, as_of: date
) -> "UserMonthlyResponse":
    """One user's stats for the rolling last-30-day window ending at as_of.

    Mirrors get_user_weekly: walk all per-CT-day MAX totals in the
    window for ranking, plus per-day breakdown of just this user's
    days that actually had data (no zero-filled gaps, matching the
    weekly endpoint's behavior on missing days)."""
    from backend.app.schemas.steps import UserMonthlyResponse

    user_id, _join_date = _lookup_user(conn, username)
    start, end = rolling_bounds(as_of, 30)
    rows = _daily_totals_in_range(conn, start, end)

    monthly_totals: dict[int, int] = defaultdict(int)
    user_daily: list[tuple[date, int]] = []
    for uid, d, total in rows:
        monthly_totals[uid] += total
        if uid == user_id:
            user_daily.append((d, total))

    rank = _rank_of_user(monthly_totals, user_id)
    user_daily.sort(key=lambda x: x[0])

    daily_breakdown = [
        DailyTotal(date=d, total=t) for d, t in user_daily
    ]

    return UserMonthlyResponse(
        username=username,
        month_start=start,
        month_end=end,
        monthly_total=monthly_totals.get(user_id, 0),
        rank_this_month=rank,
        daily_breakdown=daily_breakdown,
    )


def get_user_summary(
    conn: Connection, username: str, as_of: date
) -> UserSummaryResponse:
    user_id, join_date = _lookup_user(conn, username)

    # All-time best day: walk every row to find the user's personal peak.
    daily_max = _all_time_daily_max(conn)
    user_days: list[tuple[date, int]] = [
        (d, t) for (uid, d), t in daily_max.items() if uid == user_id
    ]

    best_day: UserBestDay | None = None
    if user_days:
        best_d, best_t = max(user_days, key=lambda x: x[1])
        best_day = UserBestDay(date=best_d, total=best_t)

    # 30-day capped score and rank.
    start, end = rolling_bounds(as_of, 30)
    scores = cap_and_sum(_daily_totals_in_range(conn, start, end), STEPS_DAILY_CAP)
    score = scores.get(user_id, 0)
    rank = _rank_of_user(scores, user_id)

    return UserSummaryResponse(
        username=username,
        join_date=join_date,
        score=score,
        best_day=best_day,
        rank=rank,
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


def detect_and_insert_milestone(
    conn: Connection,
    user_id: int,
    timestamp: datetime,
) -> Optional[int]:
    """After inserting a step row, check whether the user just crossed
    a milestone threshold for the CT day this step bucketed to. If yes,
    insert ONE post for the HIGHEST newly-crossed threshold and return
    the new post's id. Otherwise return None.

    Idempotent: existing milestone posts for the same user on the same
    CT date short-circuit re-firing of their thresholds. So a write
    that takes the user from 5500 to 6000 doesn't re-fire the 5k post."""
    ct_date = _ct_date(timestamp)
    lower, upper = _utc_window(ct_date, ct_date)

    # _utc_window spans multiple CT days, so take the max in Python
    # after filtering each row to the actual CT date. A SQL-level MAX
    # would otherwise pick up totals from a neighboring CT day and
    # falsely fire a milestone here.
    max_today_rows = (
        conn.execute(
            text(
                "SELECT total, timestamp FROM steps "
                "WHERE user_id = :uid "
                "AND timestamp >= :lower AND timestamp < :upper "
                "AND total <= :cap"
            ),
            {"uid": user_id, "lower": lower, "upper": upper, "cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )
    max_today = max(
        (int(r["total"]) for r in max_today_rows if _ct_date(r["timestamp"]) == ct_date),
        default=0,
    )

    # Already-crossed thresholds for this user on this CT date.
    # Scope the scan to today's UTC window — without that bound we'd
    # re-scan a user's lifetime of milestone posts on every step write.
    # The Python loop below still re-checks `details.date` for safety
    # (the window can include rows from the prior/next UTC day).
    already_rows = (
        conn.execute(
            text(
                "SELECT details FROM posts "
                "WHERE type = 'steps_milestone' "
                "AND user_id = :uid "
                "AND timestamp >= :lower AND timestamp < :upper"
            ),
            {"uid": user_id, "lower": lower, "upper": upper},
        )
        .mappings()
        .all()
    )
    # Find the highest threshold already posted for this user on this CT
    # date. All thresholds <= that value are implicitly already crossed —
    # you can't reach 5k without passing 1k first — so treat every
    # threshold up to and including that value as seen.
    highest_already: int = 0
    for r in already_rows:
        raw = r["details"]
        if raw is None:
            continue
        d = _json.loads(raw) if isinstance(raw, str) else raw
        if d.get("date") == ct_date.isoformat() and "threshold" in d:
            t = int(d["threshold"])
            if t > highest_already:
                highest_already = t

    # Every threshold at or below highest_already is considered crossed.
    already_crossed: set = {
        t for t in MILESTONE_THRESHOLDS if t <= highest_already
    }

    newly_crossed = [
        t
        for t in MILESTONE_THRESHOLDS
        if t <= max_today and t not in already_crossed
    ]
    if not newly_crossed:
        return None

    threshold = max(newly_crossed)
    username_row = (
        conn.execute(
            text("SELECT username FROM profiles WHERE id = :uid"),
            {"uid": user_id},
        )
        .mappings()
        .first()
    )
    if username_row is None:
        return None
    username = username_row["username"]

    details_str = _json.dumps(
        {"threshold": threshold, "date": ct_date.isoformat()}
    )
    body = f"hit {threshold:,} steps"

    # Defense-in-depth against the check-then-insert race: migration
    # 0011 puts a partial UNIQUE index on (user_id, threshold, date)
    # for type='steps_milestone'. If a concurrent step write reads
    # "no milestone yet" at the same moment we do, both will reach
    # INSERT and the loser gets IntegrityError → treat as no-op.
    try:
        row = (
            conn.execute(
                text(
                    "INSERT INTO posts (user_id, username, type, timestamp, details, body) "
                    "VALUES (:uid, :u, 'steps_milestone', :ts, :details, :body) "
                    "RETURNING id"
                ),
                {
                    "uid": user_id,
                    "u": username,
                    "ts": timestamp,
                    "details": details_str,
                    "body": body,
                },
            )
            .mappings()
            .one()
        )
    except IntegrityError:
        # Someone else's concurrent insert won; the canonical post
        # for this (user, day, threshold) already exists.
        return None
    return int(row["id"])
