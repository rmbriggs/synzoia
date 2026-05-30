"""Sleep aggregation service.

Mirrors `services/steps.py` in shape but the aggregation is simpler:
each sleep row already represents ONE night (UNIQUE on (user_id,
night_of)), so there's no MAX-per-day step like steps needs. Daily
queries are just WHERE night_of = ?; weekly/monthly are SUM(
duration_min) WHERE night_of BETWEEN ?.

Per CLAUDE.md:
- The route layer talks HTTP. This module never sees the request.
- Identifiers (table/column names) are never interpolated from
  request input. SQL is parameterized via `text()` + bind params.
- Queries use the SQLite-compatible subset so the test suite can run
  against in-memory SQLite the same way the rest of the backend
  does. Ranking is computed in Python after fetching ordered rows.

night_of bucketing: `wake_time`'s CT date minus one day. Stored at
insert time (see `create_sleep` below) so read queries can just
filter on the column directly — no UTC↔CT math at query time, no
fragile date casts in SQL.
"""

from __future__ import annotations

import json as _json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

from backend.app.schemas.sleep import (
    BestNightEver,
    CreateSleepResponse,
    DailyTotal,
    GlobalDailyResponse,
    GlobalSummaryResponse,
    GlobalWeeklyResponse,
    LeaderboardEntry,
    SleepPost,
    SummaryLeader,
    UserBestNight,
    UserDailyResponse,
    UserMonthlyResponse,
    UserSummaryResponse,
    UserWeeklyResponse,
)

# Sleep durations above this are treated as data errors and dropped
# from aggregations. The DB CHECK already caps duration_min at 1440
# (24h), so this only catches the legal-but-implausible range.
# 16 hours of sleep in a single night is a clear sign of bad data.
OUTLIER_CAP = 960  # 16 hours

# Central Time anchors all date logic — see services/steps.py for the
# rationale (same constraint applies: iOS Shortcut sends UTC, frontend
# displays in CT).
APP_TZ = ZoneInfo("America/Chicago")


def _ct_date(ts) -> date:
    """Convert a stored-as-UTC timestamp (str from SQLite, datetime
    from Postgres; naive or aware) to its calendar date in CT."""
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(APP_TZ).date()


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


def _month_bounds(month_start: date) -> tuple[date, date]:
    """Return (first_of_month, last_of_month_inclusive). Caller passes
    a date in the desired CT month; we re-anchor defensively."""
    first = month_start.replace(day=1)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    last = next_first - timedelta(days=1)
    return first, last


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


def _ensure_date(d) -> date:
    """SQLite returns DATE columns as strings; Postgres returns date
    objects. Normalize."""
    if isinstance(d, str):
        return date.fromisoformat(d)
    return d


def _nightly_rows_in_range(
    conn: Connection, start_date: date, end_date: date
) -> list[tuple[int, date, int]]:
    """All (user_id, night_of, duration_min) tuples in
    [start_date, end_date]. Outliers (duration_min > OUTLIER_CAP) are
    dropped from aggregations."""
    rows = (
        conn.execute(
            text(
                "SELECT user_id, night_of, duration_min FROM sleep "
                "WHERE night_of >= :start "
                "AND night_of <= :end "
                "AND duration_min <= :cap"
            ),
            {"start": start_date, "end": end_date, "cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )
    return [
        (int(r["user_id"]), _ensure_date(r["night_of"]), int(r["duration_min"]))
        for r in rows
    ]


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
) -> Optional[int]:
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
    rows = _nightly_rows_in_range(conn, target_date, target_date)
    totals_by_user = {uid: total for uid, _d, total in rows}
    usernames = _usernames_for(conn, totals_by_user.keys())
    leaderboard = _build_leaderboard(totals_by_user, usernames)
    return GlobalDailyResponse(
        date=target_date,
        total_minutes=sum(totals_by_user.values()),
        participating_users=len(totals_by_user),
        leaderboard=leaderboard,
    )


def get_global_weekly(
    conn: Connection, week_start: date
) -> GlobalWeeklyResponse:
    start, end = _iso_week_bounds(week_start)
    rows = _nightly_rows_in_range(conn, start, end)

    weekly_totals: dict[int, int] = defaultdict(int)
    daily_global: dict[date, int] = defaultdict(int)
    for uid, d, total in rows:
        weekly_totals[uid] += total
        daily_global[d] += total

    usernames = _usernames_for(conn, weekly_totals.keys())
    leaderboard = _build_leaderboard(weekly_totals, usernames)

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
        total_minutes=sum(weekly_totals.values()),
        leaderboard=leaderboard,
        daily_breakdown=daily_breakdown,
    )


def get_global_summary(
    conn: Connection, today: date, week_start: date
) -> GlobalSummaryResponse:
    total_users = int(
        conn.execute(text("SELECT COUNT(*) FROM profiles")).scalar() or 0
    )

    all_rows = (
        conn.execute(
            text(
                "SELECT user_id, night_of, duration_min FROM sleep "
                "WHERE duration_min <= :cap"
            ),
            {"cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )
    total_minutes_all_time = sum(int(r["duration_min"]) for r in all_rows)

    best_row = max(
        all_rows,
        key=lambda r: int(r["duration_min"]),
        default=None,
    )
    best_night_ever: Optional[BestNightEver] = None
    if best_row is not None:
        best_uid = int(best_row["user_id"])
        usernames = _usernames_for(conn, [best_uid])
        if best_uid in usernames:
            best_night_ever = BestNightEver(
                date=_ensure_date(best_row["night_of"]),
                total=int(best_row["duration_min"]),
                username=usernames[best_uid],
            )

    today_leader = _top_leader(conn, today, today)
    week_end = week_start + timedelta(days=6)
    this_week_leader = _top_leader(conn, week_start, week_end)

    return GlobalSummaryResponse(
        total_users=total_users,
        total_minutes_all_time=total_minutes_all_time,
        today_leader=today_leader,
        this_week_leader=this_week_leader,
        best_night_ever=best_night_ever,
    )


def _top_leader(
    conn: Connection, start_date: date, end_date: date
) -> Optional[SummaryLeader]:
    rows = _nightly_rows_in_range(conn, start_date, end_date)
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

    rows = _nightly_rows_in_range(conn, target_date, target_date)
    totals_by_user = {uid: total for uid, _d, total in rows}
    rank = _rank_of_user(totals_by_user, user_id)
    user_total = totals_by_user.get(user_id, 0)

    # Pull the full row for that night (if any) so the UI can render
    # the night detail card.
    post_row = (
        conn.execute(
            text(
                "SELECT night_of, bedtime, wake_time, duration_min, "
                "rem_minutes, core_minutes, deep_minutes, awake_minutes "
                "FROM sleep "
                "WHERE user_id = :uid AND night_of = :d "
                "AND duration_min <= :cap"
            ),
            {"uid": user_id, "d": target_date, "cap": OUTLIER_CAP},
        )
        .mappings()
        .first()
    )

    post: Optional[SleepPost] = None
    if post_row is not None:
        post = SleepPost(
            night_of=_ensure_date(post_row["night_of"]),
            bedtime=post_row["bedtime"],
            wake_time=post_row["wake_time"],
            duration_min=int(post_row["duration_min"]),
            rem_minutes=(
                int(post_row["rem_minutes"])
                if post_row["rem_minutes"] is not None
                else None
            ),
            core_minutes=(
                int(post_row["core_minutes"])
                if post_row["core_minutes"] is not None
                else None
            ),
            deep_minutes=(
                int(post_row["deep_minutes"])
                if post_row["deep_minutes"] is not None
                else None
            ),
            awake_minutes=(
                int(post_row["awake_minutes"])
                if post_row["awake_minutes"] is not None
                else None
            ),
        )

    return UserDailyResponse(
        username=username,
        date=target_date,
        total=user_total,
        rank_today=rank,
        post=post,
    )


def get_user_weekly(
    conn: Connection, username: str, week_start: date
) -> UserWeeklyResponse:
    user_id, _join_date = _lookup_user(conn, username)
    start, end = _iso_week_bounds(week_start)
    rows = _nightly_rows_in_range(conn, start, end)

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
    conn: Connection, username: str, month_anchor: date
) -> UserMonthlyResponse:
    user_id, _join_date = _lookup_user(conn, username)
    start, end = _month_bounds(month_anchor)
    rows = _nightly_rows_in_range(conn, start, end)

    monthly_totals: dict[int, int] = defaultdict(int)
    user_daily: dict[date, int] = {}
    for uid, d, total in rows:
        monthly_totals[uid] += total
        if uid == user_id:
            user_daily[d] = total

    rank = _rank_of_user(monthly_totals, user_id)

    span = (end - start).days + 1
    daily_breakdown = [
        DailyTotal(
            date=start + timedelta(days=offset),
            total=user_daily.get(start + timedelta(days=offset), 0),
        )
        for offset in range(span)
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
    conn: Connection, username: str
) -> UserSummaryResponse:
    user_id, join_date = _lookup_user(conn, username)

    rows = (
        conn.execute(
            text(
                "SELECT user_id, night_of, duration_min FROM sleep "
                "WHERE duration_min <= :cap"
            ),
            {"cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )

    totals_by_user: dict[int, int] = defaultdict(int)
    user_nights: list[tuple[date, int]] = []
    for r in rows:
        uid = int(r["user_id"])
        d = _ensure_date(r["night_of"])
        total = int(r["duration_min"])
        totals_by_user[uid] += total
        if uid == user_id:
            user_nights.append((d, total))

    rank_all_time = _rank_of_user(totals_by_user, user_id)

    best_night: Optional[UserBestNight] = None
    if user_nights:
        best_d, best_t = max(user_nights, key=lambda x: x[1])
        best_night = UserBestNight(date=best_d, total=best_t)

    return UserSummaryResponse(
        username=username,
        join_date=join_date,
        total_minutes_all_time=totals_by_user.get(user_id, 0),
        best_night=best_night,
        rank_all_time=rank_all_time,
        nights_logged=len(user_nights),
    )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def _night_of_for(wake_time: datetime) -> date:
    """night_of = wake_time's CT date minus 1 day. The +1 day at the
    end of a normal sleep session means we anchor on the date the
    user GOT INTO BED, not the date they woke. A 2 AM bedtime → 9 AM
    wake still buckets to the prior night."""
    wake_date = _ct_date(wake_time)
    return wake_date - timedelta(days=1)


def create_sleep(
    conn: Connection,
    user_id: int,
    bedtime: datetime,
    wake_time: datetime,
    duration_min: int,
    rem_minutes: Optional[int] = None,
    core_minutes: Optional[int] = None,
    deep_minutes: Optional[int] = None,
    awake_minutes: Optional[int] = None,
) -> CreateSleepResponse:
    """Insert one sleep row. `user_id` was resolved from the Bearer
    token by the route layer; never trust user_id from the body.
    `night_of` is computed here so clients can't pick the wrong night.

    Raises ValueError on a duplicate (user_id, night_of) — caller
    should translate to 409. Raises ValueError on wake_time <=
    bedtime too (the DB CHECK would catch it, but failing in Python
    is cheaper and produces a cleaner error message)."""
    if wake_time <= bedtime:
        raise ValueError("wake_time must be after bedtime")

    night_of = _night_of_for(wake_time)

    row = (
        conn.execute(
            text(
                "INSERT INTO sleep ("
                "user_id, bedtime, wake_time, duration_min, "
                "rem_minutes, core_minutes, deep_minutes, awake_minutes, "
                "night_of"
                ") VALUES ("
                ":user_id, :bedtime, :wake_time, :duration_min, "
                ":rem_minutes, :core_minutes, :deep_minutes, :awake_minutes, "
                ":night_of"
                ") RETURNING id, user_id, bedtime, wake_time, duration_min, "
                "rem_minutes, core_minutes, deep_minutes, awake_minutes, "
                "night_of"
            ),
            {
                "user_id": user_id,
                "bedtime": bedtime,
                "wake_time": wake_time,
                "duration_min": duration_min,
                "rem_minutes": rem_minutes,
                "core_minutes": core_minutes,
                "deep_minutes": deep_minutes,
                "awake_minutes": awake_minutes,
                "night_of": night_of,
            },
        )
        .mappings()
        .one()
    )

    return CreateSleepResponse(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        bedtime=row["bedtime"],
        wake_time=row["wake_time"],
        duration_min=int(row["duration_min"]),
        rem_minutes=(
            int(row["rem_minutes"]) if row["rem_minutes"] is not None else None
        ),
        core_minutes=(
            int(row["core_minutes"]) if row["core_minutes"] is not None else None
        ),
        deep_minutes=(
            int(row["deep_minutes"]) if row["deep_minutes"] is not None else None
        ),
        awake_minutes=(
            int(row["awake_minutes"])
            if row["awake_minutes"] is not None
            else None
        ),
        night_of=_ensure_date(row["night_of"]),
    )


def _format_sleep_body(duration_min: int) -> str:
    """Pre-rendered feed text, e.g. 'slept 7h 32m'. Mirrors how
    steps_milestone posts store a ready-to-display body."""
    hours, minutes = divmod(duration_min, 60)
    return f"slept {hours}h {minutes}m"


def create_sleep_post(
    conn: Connection,
    user_id: int,
    duration_min: int,
    night_of: date,
    wake_time: datetime,
) -> None:
    """Insert one feed post for a logged night. Called from the sleep
    route in the SAME transaction as create_sleep, so a duplicate-night
    rollback (409) takes the post with it. `type='sleep'` is already an
    allowed post type (migration 0007 CHECK). The username is looked up
    server-side — never trusted from the request body."""
    username_row = (
        conn.execute(
            text("SELECT username FROM profiles WHERE id = :uid"),
            {"uid": user_id},
        )
        .mappings()
        .first()
    )
    if username_row is None:
        return
    details_str = _json.dumps(
        {"duration_min": duration_min, "night_of": night_of.isoformat()}
    )
    # Store wake_time as an ISO-8601 string so SQLite keeps the 'T'
    # separator (datetime objects get serialized as '2026-05-28 12:32:00'
    # by the SQLite adapter, which would break the timestamp assertion).
    ts_str = (
        wake_time.isoformat()
        if isinstance(wake_time, datetime)
        else str(wake_time)
    )
    conn.execute(
        text(
            "INSERT INTO posts "
            "(user_id, username, type, timestamp, details, body) "
            "VALUES (:uid, :u, 'sleep', :ts, :details, :body)"
        ),
        {
            "uid": user_id,
            "u": username_row["username"],
            "ts": ts_str,
            "details": details_str,
            "body": _format_sleep_body(duration_min),
        },
    )
