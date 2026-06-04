"""Unit tests for backend.app.services.sleep (read aggregations).

These tests speak to the service layer directly with an in-memory SQLite
engine — no FastAPI involved. Uses the same fixture pattern as the other
service tests in this repo.

sleep rows are keyed by `night_of` (a date) with value `duration_min`.
"""

from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app.services import sleep as svc
from backend.app.services.sleep import UserNotFound


def _engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE profiles ("
                "id integer primary key autoincrement, "
                "username text not null unique, "
                "token text not null unique, "
                "join_date text not null default (datetime('now')))"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE sleep ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "bedtime text not null, "
                "wake_time text not null, "
                "duration_min integer not null, "
                "rem_minutes integer, "
                "core_minutes integer, "
                "deep_minutes integer, "
                "awake_minutes integer, "
                "night_of text not null)"
            )
        )
    return engine


def _add_profile(conn, username: str, token: str) -> int:
    return int(
        conn.execute(
            text(
                "INSERT INTO profiles (username, token) "
                "VALUES (:u, :t) RETURNING id"
            ),
            {"u": username, "t": token},
        ).scalar()
    )


def _add_sleep(conn, user_id: int, night_of: str, duration_min: int) -> None:
    """Insert one sleep row. bedtime/wake_time are synthetic stubs — the
    read aggregations only query night_of and duration_min."""
    conn.execute(
        text(
            "INSERT INTO sleep "
            "(user_id, bedtime, wake_time, duration_min, night_of) "
            "VALUES (:u, :b, :w, :d, :n)"
        ),
        {
            "u": user_id,
            "b": f"{night_of} 23:00:00",
            "w": f"{night_of} 07:00:00",
            "d": duration_min,
            "n": night_of,
        },
    )


# ---------------------------------------------------------------------------
# Basic smoke tests
# ---------------------------------------------------------------------------


def test_user_weekly_404s_for_unknown_user():
    engine = _engine()
    with engine.connect() as conn:
        with pytest.raises(UserNotFound):
            svc.get_user_weekly(conn, "nobody", as_of=date(2026, 6, 2))


def test_user_monthly_404s_for_unknown_user():
    engine = _engine()
    with engine.connect() as conn:
        with pytest.raises(UserNotFound):
            svc.get_user_monthly(conn, "nobody", as_of=date(2026, 6, 2))


def test_user_weekly_returns_zero_when_no_rows():
    engine = _engine()
    with engine.begin() as conn:
        _add_profile(conn, "amy", "ta_amy" + "0" * 26)

    with engine.connect() as conn:
        result = svc.get_user_weekly(conn, "amy", as_of=date(2026, 6, 2))

    assert result.weekly_total == 0
    assert result.rank_this_week is None
    assert len(result.daily_breakdown) == 7


def test_user_monthly_returns_zero_when_no_rows():
    engine = _engine()
    with engine.begin() as conn:
        _add_profile(conn, "amy", "ta_amy" + "0" * 26)

    with engine.connect() as conn:
        result = svc.get_user_monthly(conn, "amy", as_of=date(2026, 6, 2))

    assert result.monthly_total == 0
    assert result.rank_this_month is None
    assert len(result.daily_breakdown) == 30  # zero-filled span


# ---------------------------------------------------------------------------
# Rolling-window tests (new behaviour)
# ---------------------------------------------------------------------------


def test_rolling_user_weekly_uses_last_7_days():
    """get_user_weekly(conn, user, as_of=date(2026,6,2)) uses rolling bounds:
    week_start = 2026-05-27, week_end = 2026-06-02.
    A night_of on as_of-2 (2026-05-31) is included; a night_of on as_of-8
    (2026-05-25) is excluded from the weekly_total. daily_breakdown has 7
    entries."""
    as_of = date(2026, 6, 2)
    engine = _engine()
    with engine.begin() as conn:
        amy = _add_profile(conn, "amy", "ta_amy" + "0" * 26)
        # Inside window: as_of-2 = 2026-05-31
        _add_sleep(conn, amy, "2026-05-31", 480)
        # Outside window: as_of-8 = 2026-05-25
        _add_sleep(conn, amy, "2026-05-25", 999)

    with engine.connect() as conn:
        result = svc.get_user_weekly(conn, "amy", as_of=as_of)

    assert result.week_start == date(2026, 5, 27)
    assert result.week_end == date(2026, 6, 2)
    assert len(result.daily_breakdown) == 7
    # Only the in-window row contributes to the total
    assert result.weekly_total == 480
    # Verify the out-of-window row is not counted
    by_date = {d.date: d.total for d in result.daily_breakdown}
    assert date(2026, 5, 31) in by_date
    assert by_date[date(2026, 5, 31)] == 480
    assert date(2026, 5, 25) not in by_date


def test_rolling_user_monthly_uses_last_30_days():
    """get_user_monthly(conn, user, as_of=date(2026,6,2)) uses rolling bounds:
    month_start = 2026-05-04, month_end = 2026-06-02.
    A night_of on as_of-20 (2026-05-13) is INCLUDED; a night_of on
    as_of-35 (2026-04-28) is EXCLUDED from monthly_total.
    daily_breakdown has 30 entries (zero-filled span)."""
    as_of = date(2026, 6, 2)
    engine = _engine()
    with engine.begin() as conn:
        amy = _add_profile(conn, "amy", "tb_amy" + "0" * 26)
        # Inside window: as_of-20 = 2026-05-13
        _add_sleep(conn, amy, "2026-05-13", 510)
        # Outside window: as_of-35 = 2026-04-28
        _add_sleep(conn, amy, "2026-04-28", 888)

    with engine.connect() as conn:
        result = svc.get_user_monthly(conn, "amy", as_of=as_of)

    assert result.month_start == date(2026, 5, 4)
    assert result.month_end == date(2026, 6, 2)
    # Only the in-window row contributes to the total
    assert result.monthly_total == 510
    # Zero-filled span: always 30 entries
    assert len(result.daily_breakdown) == 30
    by_date = {d.date: d.total for d in result.daily_breakdown}
    assert date(2026, 5, 13) in by_date
    assert by_date[date(2026, 5, 13)] == 510
    # Out-of-window date must not appear
    assert date(2026, 4, 28) not in by_date


# ---------------------------------------------------------------------------
# 30-day capped ranking tests (new behaviour)
# ---------------------------------------------------------------------------


def test_sleep_global_ranking_caps_and_ranks():
    """get_global_ranking caps duration_min at SLEEP_DAILY_CAP_MIN (540)
    before ranking. User with a capped night should rank below a user with
    a smaller, legitimate night if the cap brings them equal or below."""

    as_of = date(2026, 6, 1)
    engine = _engine()
    with engine.begin() as conn:
        amy_id = _add_profile(conn, "amy", "tc_amy" + "0" * 26)
        bob_id = _add_profile(conn, "bob", "tc_bob" + "0" * 26)
        # amy: 420 min — under cap
        _add_sleep(conn, amy_id, "2026-06-01", 420)
        # bob: 900 min — capped to 540
        _add_sleep(conn, bob_id, "2026-06-01", 900)

    with engine.connect() as conn:
        resp = svc.get_global_ranking(conn, as_of)

    by_user = {e.username: (e.rank, e.total) for e in resp.leaderboard}
    assert by_user["bob"][1] == 540   # capped
    assert by_user["amy"][1] == 420
    assert by_user["bob"][0] == 1     # 540 > 420 so bob ranks first
    assert by_user["amy"][0] == 2


def test_sleep_user_summary_rank_and_score():
    """get_user_summary with as_of only counts nights in the 30-day
    rolling window; nights older than 30 days are excluded from score."""
    from datetime import timedelta

    as_of = date(2026, 6, 1)
    engine = _engine()
    with engine.begin() as conn:
        amy_id = _add_profile(conn, "amy", "td_amy" + "0" * 26)
        # In-window night
        _add_sleep(conn, amy_id, "2026-06-01", 430)
        # Out-of-window night (40 days ago)
        _add_sleep(conn, amy_id, str(as_of - timedelta(days=40)), 480)

    with engine.connect() as conn:
        resp = svc.get_user_summary(conn, "amy", as_of)

    assert resp.score == 430    # only the in-window night counts
    assert resp.rank == 1
