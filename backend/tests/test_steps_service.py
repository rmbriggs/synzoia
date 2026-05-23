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
        # Monday 2026-05-18 → Sunday 2026-05-24
        _add_step(conn, alice, "2026-05-18 09:00:00", 3000)
        _add_step(conn, alice, "2026-05-18 21:00:00", 7000)  # day max
        _add_step(conn, alice, "2026-05-19 12:00:00", 4000)
        _add_step(conn, alice, "2026-05-24 22:00:00", 10000)
        # One day OUTSIDE the week
        _add_step(conn, alice, "2026-05-25 09:00:00", 8000)

    with engine.connect() as conn:
        result = svc.get_global_weekly(conn, date(2026, 5, 18))

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
    # 5/25 is outside the week and must not appear at all.
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
        result = svc.get_global_summary(
            conn,
            today=date(2026, 5, 23),
            week_start=date(2026, 5, 18),
        )

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
        result = svc.get_global_summary(
            conn,
            today=date(2026, 5, 23),
            week_start=date(2026, 5, 18),
        )
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
        result = svc.get_user_weekly(conn, "alice", date(2026, 5, 18))

    assert result.weekly_total == 10000
    assert result.rank_this_week == 1
    # daily_breakdown has 7 entries, zero-filled
    assert len(result.daily_breakdown) == 7
    by_date = {d.date: d.total for d in result.daily_breakdown}
    assert by_date[date(2026, 5, 19)] == 4000
    assert by_date[date(2026, 5, 20)] == 0
    assert by_date[date(2026, 5, 21)] == 6000


def test_user_summary_picks_best_day_and_counts_days_active():
    engine = _engine()
    with engine.begin() as conn:
        alice = _add_profile(conn, "alice", "ta" + "0" * 30)
        bob = _add_profile(conn, "bob", "tb" + "0" * 30)
        _add_step(conn, alice, "2026-05-18 22:00:00", 5000)
        _add_step(conn, alice, "2026-05-19 22:00:00", 7000)
        _add_step(conn, alice, "2026-05-23 12:00:00", 3000)
        _add_step(conn, alice, "2026-05-23 22:00:00", 8000)  # day max
        _add_step(conn, bob, "2026-05-23 22:00:00", 21000)  # > alice's all-time

    with engine.connect() as conn:
        result = svc.get_user_summary(conn, "alice")

    assert result.username == "alice"
    assert result.total_steps_all_time == 5000 + 7000 + 8000
    assert result.best_day is not None
    assert result.best_day.date == date(2026, 5, 23)
    assert result.best_day.total == 8000
    assert result.days_active == 3  # 5/18, 5/19, 5/23
    assert result.rank_all_time == 2  # bob ahead


def test_user_summary_handles_user_with_no_posts():
    engine = _engine()
    with engine.begin() as conn:
        _add_profile(conn, "lonely", "tl" + "0" * 30)

    with engine.connect() as conn:
        result = svc.get_user_summary(conn, "lonely")

    assert result.total_steps_all_time == 0
    assert result.best_day is None
    assert result.rank_all_time is None
    assert result.days_active == 0
