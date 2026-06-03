"""Unit tests for backend.app.services.steps.

These tests speak to the service layer directly with an in-memory SQLite
engine, the same fixture pattern the other tests in this repo use. No
FastAPI involved; this is just SQL + Python aggregation."""

from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app.services import steps as svc
from backend.app.services.steps import OUTLIER_CAP, UserNotFound


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
                "CREATE TABLE steps ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "timestamp text not null, "
                "total integer not null)"
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


def _add_step(conn, user_id: int, ts: str, total: int) -> None:
    conn.execute(
        text(
            "INSERT INTO steps (user_id, timestamp, total) "
            "VALUES (:u, :ts, :t)"
        ),
        {"u": user_id, "ts": ts, "t": total},
    )


def test_global_daily_returns_zeros_on_empty_db():
    engine = _engine()
    with engine.connect() as conn:
        result = svc.get_global_daily(conn, date(2026, 5, 23))
    assert result.total_steps == 0
    assert result.participating_users == 0
    assert result.leaderboard == []


def test_global_daily_aggregates_with_max_per_user():
    engine = _engine()
    with engine.begin() as conn:
        alice = _add_profile(conn, "alice", "t1" + "0" * 30)
        bob = _add_profile(conn, "bob", "t2" + "0" * 30)
        # Alice posts three cumulative snapshots on 2026-05-23.
        _add_step(conn, alice, "2026-05-23 08:00:00", 1000)
        _add_step(conn, alice, "2026-05-23 12:00:00", 5000)
        _add_step(conn, alice, "2026-05-23 20:00:00", 9000)
        # Bob posts one snapshot.
        _add_step(conn, bob, "2026-05-23 21:00:00", 7000)
        # A different day — must not be counted.
        _add_step(conn, alice, "2026-05-22 22:00:00", 12000)

    with engine.connect() as conn:
        result = svc.get_global_daily(conn, date(2026, 5, 23))

    assert result.participating_users == 2
    assert result.total_steps == 9000 + 7000  # MAX(alice today) + bob
    assert [(e.rank, e.username, e.total) for e in result.leaderboard] == [
        (1, "alice", 9000),
        (2, "bob", 7000),
    ]


def test_global_daily_drops_outliers_before_aggregating():
    engine = _engine()
    with engine.begin() as conn:
        alice = _add_profile(conn, "alice", "t1" + "0" * 30)
        # A glitch post above the cap; the lower row should still count.
        _add_step(conn, alice, "2026-05-23 08:00:00", 8000)
        _add_step(conn, alice, "2026-05-23 12:00:00", OUTLIER_CAP + 1)

    with engine.connect() as conn:
        result = svc.get_global_daily(conn, date(2026, 5, 23))

    assert result.total_steps == 8000
    assert result.leaderboard[0].total == 8000


def test_global_daily_ranks_ties_with_dense_rank():
    engine = _engine()
    with engine.begin() as conn:
        a = _add_profile(conn, "alice", "ta" + "0" * 30)
        b = _add_profile(conn, "bob", "tb" + "0" * 30)
        c = _add_profile(conn, "carol", "tc" + "0" * 30)
        _add_step(conn, a, "2026-05-23 08:00:00", 5000)
        _add_step(conn, b, "2026-05-23 08:00:00", 5000)
        _add_step(conn, c, "2026-05-23 08:00:00", 3000)

    with engine.connect() as conn:
        result = svc.get_global_daily(conn, date(2026, 5, 23))

    # Dense rank: two tied at 5000 share rank 1, carol is rank 2 (not 3).
    assert [(e.rank, e.username) for e in result.leaderboard] == [
        (1, "alice"),
        (1, "bob"),
        (2, "carol"),
    ]


def test_global_weekly_sums_daily_maxes_across_seven_days():
    engine = _engine()
    with engine.begin() as conn:
        alice = _add_profile(conn, "alice", "ta" + "0" * 30)
        # Rolling window: as_of=2026-05-24 → 2026-05-18..2026-05-24
        _add_step(conn, alice, "2026-05-18 09:00:00", 3000)
        _add_step(conn, alice, "2026-05-18 21:00:00", 7000)  # day max
        _add_step(conn, alice, "2026-05-19 12:00:00", 4000)
        _add_step(conn, alice, "2026-05-24 22:00:00", 10000)
        # One day OUTSIDE the window (as_of+1)
        _add_step(conn, alice, "2026-05-25 09:00:00", 8000)

    with engine.connect() as conn:
        result = svc.get_global_weekly(conn, date(2026, 5, 24))

    assert result.week_start == date(2026, 5, 18)
    assert result.week_end == date(2026, 5, 24)
    assert result.total_steps == 7000 + 4000 + 10000
    assert len(result.daily_breakdown) == 7
    # Zero-fill for the empty days
    by_date = {d.date: d.total for d in result.daily_breakdown}
    assert by_date[date(2026, 5, 18)] == 7000
    assert by_date[date(2026, 5, 19)] == 4000
    assert by_date[date(2026, 5, 20)] == 0
    assert by_date[date(2026, 5, 24)] == 10000
    # 5/25 is outside the window and must not appear at all.
    assert date(2026, 5, 25) not in by_date


def test_global_summary_picks_best_day_and_leaders():
    engine = _engine()
    with engine.begin() as conn:
        alice = _add_profile(conn, "alice", "ta" + "0" * 30)
        bob = _add_profile(conn, "bob", "tb" + "0" * 30)
        # Best day ever: bob on 2026-05-20 with 20000.
        _add_step(conn, bob, "2026-05-20 22:00:00", 20000)
        _add_step(conn, alice, "2026-05-20 22:00:00", 5000)
        # Today: alice leads with 12000.
        _add_step(conn, alice, "2026-05-23 22:00:00", 12000)
        _add_step(conn, bob, "2026-05-23 22:00:00", 8000)

    with engine.connect() as conn:
        result = svc.get_global_summary(conn, as_of=date(2026, 5, 23))

    assert result.total_users == 2
    assert result.total_steps_all_time == 20000 + 5000 + 12000 + 8000
    assert result.best_day_ever is not None
    assert result.best_day_ever.username == "bob"
    assert result.best_day_ever.total == 20000
    assert result.best_day_ever.date == date(2026, 5, 20)
    assert result.today_leader is not None
    assert result.today_leader.username == "alice"
    assert result.today_leader.total == 12000


def test_global_summary_handles_empty_db():
    engine = _engine()
    with engine.connect() as conn:
        result = svc.get_global_summary(conn, as_of=date(2026, 5, 23))
    assert result.total_users == 0
    assert result.total_steps_all_time == 0
    assert result.today_leader is None
    assert result.this_week_leader is None
    assert result.best_day_ever is None


def test_user_daily_returns_rank_and_posts():
    engine = _engine()
    with engine.begin() as conn:
        alice = _add_profile(conn, "alice", "ta" + "0" * 30)
        bob = _add_profile(conn, "bob", "tb" + "0" * 30)
        _add_step(conn, alice, "2026-05-23 08:00:00", 1000)
        _add_step(conn, alice, "2026-05-23 12:00:00", 5000)
        _add_step(conn, alice, "2026-05-23 20:00:00", 9000)
        _add_step(conn, bob, "2026-05-23 22:00:00", 12000)

    with engine.connect() as conn:
        result = svc.get_user_daily(conn, "alice", date(2026, 5, 23))

    assert result.username == "alice"
    assert result.total == 9000
    assert result.rank_today == 2  # bob leads
    assert [p.total for p in result.posts] == [1000, 5000, 9000]


def test_user_daily_returns_zero_and_null_rank_when_no_posts():
    engine = _engine()
    with engine.begin() as conn:
        _add_profile(conn, "alice", "ta" + "0" * 30)

    with engine.connect() as conn:
        result = svc.get_user_daily(conn, "alice", date(2026, 5, 23))

    assert result.total == 0
    assert result.rank_today is None
    assert result.posts == []


def test_user_daily_404s_for_unknown_user():
    engine = _engine()
    with engine.connect() as conn:
        with pytest.raises(UserNotFound):
            svc.get_user_daily(conn, "nobody", date(2026, 5, 23))


def test_user_weekly_ranks_correctly():
    engine = _engine()
    with engine.begin() as conn:
        alice = _add_profile(conn, "alice", "ta" + "0" * 30)
        bob = _add_profile(conn, "bob", "tb" + "0" * 30)
        _add_step(conn, alice, "2026-05-19 22:00:00", 4000)
        _add_step(conn, alice, "2026-05-21 22:00:00", 6000)
        _add_step(conn, bob, "2026-05-19 22:00:00", 8000)

    with engine.connect() as conn:
        # as_of=2026-05-24 → rolling window 2026-05-18..2026-05-24
        result = svc.get_user_weekly(conn, "alice", as_of=date(2026, 5, 24))

    assert result.week_start == date(2026, 5, 18)
    assert result.week_end == date(2026, 5, 24)
    assert result.weekly_total == 10000
    assert result.rank_this_week == 1
    # daily_breakdown has 7 entries, zero-filled
    assert len(result.daily_breakdown) == 7
    by_date = {d.date: d.total for d in result.daily_breakdown}
    assert by_date[date(2026, 5, 19)] == 4000
    assert by_date[date(2026, 5, 20)] == 0
    assert by_date[date(2026, 5, 21)] == 6000


def test_user_summary_picks_best_day_and_30d_score():
    as_of = date(2026, 5, 23)
    engine = _engine()
    with engine.begin() as conn:
        alice = _add_profile(conn, "alice", "ta" + "0" * 30)
        bob = _add_profile(conn, "bob", "tb" + "0" * 30)
        _add_step(conn, alice, "2026-05-18 22:00:00", 5000)
        _add_step(conn, alice, "2026-05-19 22:00:00", 7000)
        _add_step(conn, alice, "2026-05-23 12:00:00", 3000)
        _add_step(conn, alice, "2026-05-23 22:00:00", 8000)  # day max
        _add_step(conn, bob, "2026-05-23 22:00:00", 21000)  # > alice's 30d total

    with engine.connect() as conn:
        result = svc.get_user_summary(conn, "alice", as_of)

    assert result.username == "alice"
    # 30-day capped score: 3 days all within 30d of 2026-05-23, each below 20k cap
    assert result.score == 5000 + 7000 + 8000  # = 20000
    assert result.best_day is not None
    assert result.best_day.date == date(2026, 5, 23)
    assert result.best_day.total == 8000
    # bob: min(21000, 20000) = 20000; alice: 20000 — tied, both rank 1
    assert result.rank == 1


def test_user_summary_handles_user_with_no_posts():
    engine = _engine()
    with engine.begin() as conn:
        _add_profile(conn, "lonely", "tl" + "0" * 30)

    with engine.connect() as conn:
        result = svc.get_user_summary(conn, "lonely", date(2026, 5, 23))

    assert result.score == 0
    assert result.best_day is None
    assert result.rank is None


# ---------------------------------------------------------------------------
# Rolling-window tests (new behaviour)
# ---------------------------------------------------------------------------


def test_rolling_user_weekly_uses_last_7_days():
    """get_user_weekly(conn, user, as_of=date(2026,6,2)) uses rolling bounds:
    week_start = 2026-05-27, week_end = 2026-06-02.
    A row on as_of-3 (2026-05-30) is included; a row on as_of-8 (2026-05-25)
    is excluded from the weekly_total. daily_breakdown has 7 entries."""
    as_of = date(2026, 6, 2)
    engine = _engine()
    with engine.begin() as conn:
        amy = _add_profile(conn, "amy", "ta_amy" + "0" * 26)
        # Inside window: as_of-3 = 2026-05-30
        _add_step(conn, amy, "2026-05-30 10:00:00", 5000)
        # Outside window: as_of-8 = 2026-05-25
        _add_step(conn, amy, "2026-05-25 10:00:00", 9999)

    with engine.connect() as conn:
        result = svc.get_user_weekly(conn, "amy", as_of=as_of)

    assert result.week_start == date(2026, 5, 27)
    assert result.week_end == date(2026, 6, 2)
    assert len(result.daily_breakdown) == 7
    # Only the in-window row contributes to the total
    assert result.weekly_total == 5000
    # Verify the out-of-window row is not counted
    by_date = {d.date: d.total for d in result.daily_breakdown}
    assert date(2026, 5, 30) in by_date
    assert by_date[date(2026, 5, 30)] == 5000
    assert date(2026, 5, 25) not in by_date


def test_rolling_user_monthly_uses_last_30_days():
    """get_user_monthly(conn, user, as_of=date(2026,6,2)) uses rolling bounds:
    month_start = 2026-05-04, month_end = 2026-06-02.
    A row on as_of-20 (2026-05-13) is included; a row on as_of-35 (2026-04-28)
    is excluded from monthly_total. daily_breakdown is sparse (only days with data)."""
    as_of = date(2026, 6, 2)
    engine = _engine()
    with engine.begin() as conn:
        amy = _add_profile(conn, "amy", "tb_amy" + "0" * 26)
        # Inside window: as_of-20 = 2026-05-13
        _add_step(conn, amy, "2026-05-13 10:00:00", 7000)
        # Outside window: as_of-35 = 2026-04-28
        _add_step(conn, amy, "2026-04-28 10:00:00", 8888)

    with engine.connect() as conn:
        result = svc.get_user_monthly(conn, "amy", as_of=as_of)

    assert result.month_start == date(2026, 5, 4)
    assert result.month_end == date(2026, 6, 2)
    # Only the in-window row contributes to the total
    assert result.monthly_total == 7000
    # Sparse breakdown: only days WITH data, so only one entry
    assert len(result.daily_breakdown) == 1
    assert result.daily_breakdown[0].date == date(2026, 5, 13)
    assert result.daily_breakdown[0].total == 7000


# ---------------------------------------------------------------------------
# 30-day capped ranking tests (new behaviour)
# ---------------------------------------------------------------------------


def test_global_ranking_caps_days_and_ranks_by_30d_score():
    from datetime import timedelta

    as_of = date(2026, 6, 2)
    engine = _engine()
    with engine.begin() as conn:
        amy = _add_profile(conn, "amy", "tc_amy" + "0" * 26)
        bob = _add_profile(conn, "bob", "tc_bob" + "0" * 26)
        _add_step(conn, amy, (as_of - timedelta(days=1)).isoformat() + " 10:00:00", 9000)
        _add_step(conn, amy, (as_of - timedelta(days=2)).isoformat() + " 10:00:00", 9000)
        _add_step(conn, bob, (as_of - timedelta(days=1)).isoformat() + " 10:00:00", 50000)  # capped to 20000

    with engine.connect() as conn:
        resp = svc.get_global_ranking(conn, as_of)

    by_user = {e.username: (e.rank, e.total) for e in resp.leaderboard}
    assert by_user["bob"][1] == 20000   # 50000 capped to STEPS_DAILY_CAP
    assert by_user["amy"][1] == 18000
    assert by_user["bob"][0] == 1 and by_user["amy"][0] == 2


def test_user_summary_returns_30d_rank_and_score():
    from datetime import timedelta

    as_of = date(2026, 6, 2)
    engine = _engine()
    with engine.begin() as conn:
        amy = _add_profile(conn, "amy", "td_amy" + "0" * 26)
        _add_step(conn, amy, (as_of - timedelta(days=1)).isoformat() + " 10:00:00", 9000)
        _add_step(conn, amy, (as_of - timedelta(days=40)).isoformat() + " 10:00:00", 99999)  # outside 30d window

    with engine.connect() as conn:
        resp = svc.get_user_summary(conn, "amy", as_of)

    assert resp.score == 9000   # day-40 excluded
    assert resp.rank == 1
