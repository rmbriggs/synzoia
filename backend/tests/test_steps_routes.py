"""HTTP-level tests for /api/steps/*.

The service layer is covered in test_steps_service.py; this file
exercises the FastAPI wiring: query params, response shape, the 404
contract for unknown users."""

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
                "CREATE TABLE steps ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "timestamp text not null, "
                "total integer not null)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) VALUES "
                "('alice', 'ta' || '0' || '0' || '0' || '0' || '0' || '0' "
                "|| '0' || '0' || '0' || '0' || '0' || '0' || '0' || '0' "
                "|| '0', '2026-05-01T00:00:00'), "
                "('bob', 'tb' || '0' || '0' || '0' || '0' || '0' || '0' "
                "|| '0' || '0' || '0' || '0' || '0' || '0' || '0' || '0' "
                "|| '0', '2026-05-01T00:00:00')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) VALUES "
                "(1, '2026-05-23 08:00:00', 1000), "
                "(1, '2026-05-23 12:00:00', 5000), "
                "(1, '2026-05-23 20:00:00', 9000), "
                "(2, '2026-05-23 22:00:00', 12000)"
            )
        )
    return engine


def _client_with(engine):
    return TestClient(main.app)


def test_global_daily_returns_leaderboard(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = _client_with(engine).get("/api/steps/daily?date=2026-05-23")

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-05-23"
    assert body["participating_users"] == 2
    assert body["total_steps"] == 9000 + 12000
    assert body["leaderboard"] == [
        {"rank": 1, "username": "bob", "total": 12000},
        {"rank": 2, "username": "alice", "total": 9000},
    ]


def test_global_daily_returns_empty_payload_for_a_day_with_no_posts(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = _client_with(engine).get("/api/steps/daily?date=2026-05-22")

    assert response.status_code == 200
    body = response.json()
    assert body["participating_users"] == 0
    assert body["total_steps"] == 0
    assert body["leaderboard"] == []


def test_global_weekly_returns_seven_day_breakdown(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # Rolling 7-day window ending 2026-05-24 = Mon 2026-05-18 through 2026-05-24
    response = _client_with(engine).get(
        "/api/steps/weekly?as_of=2026-05-24"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["week_start"] == "2026-05-18"
    assert body["week_end"] == "2026-05-24"
    assert len(body["daily_breakdown"]) == 7
    # Only 2026-05-23 has data; sum across all users that day is 21000
    assert body["total_steps"] == 9000 + 12000


def test_global_summary_shape(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = _client_with(engine).get("/api/steps/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] == 2
    assert body["total_steps_all_time"] == 9000 + 12000
    assert body["best_day_ever"] == {
        "date": "2026-05-23",
        "total": 12000,
        "username": "bob",
    }


def test_user_daily_returns_rank_and_posts(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = _client_with(engine).get(
        "/api/steps/users/alice/daily?date=2026-05-23"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["date"] == "2026-05-23"
    assert body["total"] == 9000
    assert body["rank_today"] == 2
    assert [p["total"] for p in body["posts"]] == [1000, 5000, 9000]


def test_user_weekly_for_known_user(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = _client_with(engine).get(
        "/api/steps/users/alice/weekly?as_of=2026-05-24"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["weekly_total"] == 9000
    assert body["rank_this_week"] == 2


def test_user_summary_for_known_user(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = _client_with(engine).get("/api/steps/users/alice/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert "score" in body
    assert "rank" in body


def test_user_lookup_is_case_insensitive(monkeypatch):
    # Usernames are stored lowercase; a mixed-case path segment (an old
    # link or a hand-typed URL) must still resolve, not 404.
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = _client_with(engine).get("/api/steps/users/ALICE/summary")

    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_user_endpoints_404_on_unknown_username(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = _client_with(engine)

    for path in (
        "/api/steps/users/nobody/daily",
        "/api/steps/users/nobody/weekly",
        "/api/steps/users/nobody/summary",
    ):
        response = client.get(path)
        assert response.status_code == 404, path
        body = response.json()
        assert body["error"]["code"] == "user_not_found"


def _engine_with_amy_data():
    """Separate in-memory DB seeded with user 'amy' for as_of tests."""
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
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) VALUES "
                "('amy', 'tamy000000000000', '2026-05-01T00:00:00')"
            )
        )
        # Seed data inside the rolling 7-day window ending 2026-06-02
        # (2026-05-27 through 2026-06-02) and 30-day window
        # (2026-05-04 through 2026-06-02).
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) VALUES "
                "(1, '2026-05-28 08:00:00', 3000), "
                "(1, '2026-05-29 08:00:00', 6000), "
                "(1, '2026-06-01 08:00:00', 8000)"
            )
        )
    return engine


def test_user_weekly_route_accepts_as_of_rolling_bounds(monkeypatch):
    engine = _engine_with_amy_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    resp = TestClient(main.app).get(
        "/api/steps/users/amy/weekly?as_of=2026-06-02"
    )
    assert resp.status_code == 200
    b = resp.json()
    assert b["week_start"] == "2026-05-27"
    assert b["week_end"] == "2026-06-02"
    assert len(b["daily_breakdown"]) == 7


def test_user_monthly_route_accepts_as_of(monkeypatch):
    engine = _engine_with_amy_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    resp = TestClient(main.app).get(
        "/api/steps/users/amy/monthly?as_of=2026-06-02"
    )
    assert resp.status_code == 200
    b = resp.json()
    assert b["month_start"] == "2026-05-04"
    assert b["month_end"] == "2026-06-02"


def test_ranking_route_returns_board(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    resp = TestClient(main.app).get("/api/steps/ranking?as_of=2026-06-02")

    assert resp.status_code == 200
    assert "leaderboard" in resp.json()


def test_user_summary_route_has_rank_and_score(monkeypatch):
    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    resp = TestClient(main.app).get("/api/steps/users/alice/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert "score" in body and "rank" in body
    assert "total_steps_all_time" not in body and "days_active" not in body


def test_global_daily_defaults_to_today_when_no_date_param(monkeypatch):
    from datetime import datetime as _datetime
    from zoneinfo import ZoneInfo

    engine = _engine_with_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = _client_with(engine).get("/api/steps/daily")

    assert response.status_code == 200
    body = response.json()
    # The endpoint's "today" is Central Time (synzoia anchors all date
    # display to America/Chicago). On UTC-only CI hosts, comparing
    # against date.today() (which is UTC) drifts across midnight.
    expected_today = (
        _datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    )
    assert body["date"] == expected_today
    assert "leaderboard" in body
    assert "total_steps" in body
