"""HTTP-level tests for /api/sleep/* read endpoints.

The service layer's correctness is covered separately; this file
exercises the FastAPI wiring: query params, response shape, the 404
contract for unknown users, and the leaderboard ranking the routes
expose.
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


def _engine_with_data():
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
                "night_of text not null, "
                "created_at text not null default (datetime('now')), "
                "unique (user_id, night_of))"
            )
        )
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) VALUES "
                "('alice', 'ALCE-AAAA-AAAA-AAAA', '2026-05-01T00:00:00'), "
                "('bob',   'BOBB-BBBB-BBBB-BBBB', '2026-05-01T00:00:00')"
            )
        )
        # Three nights of sleep across two users.
        # alice slept the night of 2026-05-21 → 420 min
        # alice slept the night of 2026-05-22 → 500 min
        # bob   slept the night of 2026-05-22 → 480 min
        conn.execute(
            text(
                "INSERT INTO sleep ("
                "user_id, bedtime, wake_time, duration_min, "
                "rem_minutes, core_minutes, deep_minutes, awake_minutes, "
                "night_of"
                ") VALUES "
                "(1, '2026-05-22 03:00:00', '2026-05-22 10:00:00', 420, "
                " 80, 220, 80, 40, '2026-05-21'), "
                "(1, '2026-05-23 03:00:00', '2026-05-23 11:00:00', 500, "
                " 95, 250, 95, 40, '2026-05-22'), "
                "(2, '2026-05-23 02:00:00', '2026-05-23 10:00:00', 480, "
                " 90, 240, 90, 40, '2026-05-22')"
            )
        )
    return engine


# ---------------------------------------------------------------------------
# Global
# ---------------------------------------------------------------------------


def test_global_daily_returns_leaderboard(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/sleep/daily?date=2026-05-22")

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-05-22"
    assert body["participating_users"] == 2
    assert body["total_minutes"] == 500 + 480
    assert body["leaderboard"] == [
        {"rank": 1, "username": "alice", "total": 500},
        {"rank": 2, "username": "bob", "total": 480},
    ]


def test_global_daily_empty_when_no_one_slept(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/sleep/daily?date=1999-01-01")

    assert response.status_code == 200
    body = response.json()
    assert body["participating_users"] == 0
    assert body["total_minutes"] == 0
    assert body["leaderboard"] == []


def test_global_weekly_returns_seven_day_breakdown(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # Week of 2026-05-18 (Mon) through 2026-05-24 (Sun).
    response = TestClient(main.app).get(
        "/api/sleep/weekly?week_start=2026-05-18"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["week_start"] == "2026-05-18"
    assert body["week_end"] == "2026-05-24"
    # alice 420 + 500 = 920; bob 480. Total 1400.
    assert body["total_minutes"] == 920 + 480
    # Leaderboard ranks by weekly total.
    assert body["leaderboard"][0]["username"] == "alice"
    assert body["leaderboard"][0]["total"] == 920
    assert body["leaderboard"][1]["username"] == "bob"
    assert body["leaderboard"][1]["total"] == 480
    assert len(body["daily_breakdown"]) == 7


def test_global_summary_picks_best_night_and_leaders(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/sleep/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] == 2
    assert body["total_minutes_all_time"] == 420 + 500 + 480
    # alice's 500-min night is the longest single night in the seed.
    assert body["best_night_ever"] == {
        "date": "2026-05-22",
        "total": 500,
        "username": "alice",
    }


# ---------------------------------------------------------------------------
# Per-user
# ---------------------------------------------------------------------------


def test_user_daily_returns_rank_and_post(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get(
        "/api/sleep/users/alice/daily?date=2026-05-22"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["date"] == "2026-05-22"
    assert body["total"] == 500
    assert body["rank_today"] == 1
    assert body["post"] is not None
    assert body["post"]["duration_min"] == 500
    assert body["post"]["rem_minutes"] == 95


def test_user_daily_returns_zero_and_null_rank_when_no_post(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get(
        "/api/sleep/users/alice/daily?date=1999-01-01"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["rank_today"] is None
    assert body["post"] is None


def test_user_daily_404s_for_unknown_user(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get(
        "/api/sleep/users/carol/daily?date=2026-05-22"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


def test_user_weekly_ranks_correctly(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get(
        "/api/sleep/users/alice/weekly?week_start=2026-05-18"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["weekly_total"] == 920
    assert body["rank_this_week"] == 1


def test_user_summary_picks_best_night_and_counts_nights(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get(
        "/api/sleep/users/alice/summary"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["total_minutes_all_time"] == 920
    assert body["best_night"] == {"date": "2026-05-22", "total": 500}
    assert body["nights_logged"] == 2
    assert body["rank_all_time"] == 1


def test_user_monthly_returns_breakdown(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get(
        "/api/sleep/users/alice/monthly?month=2026-05"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["month_start"] == "2026-05-01"
    assert body["month_end"] == "2026-05-31"
    assert body["monthly_total"] == 920
    assert len(body["daily_breakdown"]) == 31
