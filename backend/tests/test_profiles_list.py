"""Tests for the /api/profiles list endpoint and underlying service."""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app.services import profiles as svc


def _engine_with(profiles, steps):
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
        for p in profiles:
            conn.execute(
                text(
                    "INSERT INTO profiles (id, username, token, join_date) "
                    "VALUES (:id, :u, :t, :j)"
                ),
                p,
            )
        for s in steps:
            conn.execute(
                text(
                    "INSERT INTO steps (user_id, timestamp, total) "
                    "VALUES (:u, :ts, :t)"
                ),
                s,
            )
    return engine


def test_list_profiles_returns_alphabetical_by_username():
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "zoe",    "t": "zoe_token________________________", "j": "2026-05-20T00:00:00"},
            {"id": 2, "u": "alice",  "t": "alice_token______________________", "j": "2026-05-19T00:00:00"},
            {"id": 3, "u": "bob",    "t": "bob_token________________________", "j": "2026-05-21T00:00:00"},
        ],
        steps=[],
    )
    with engine.connect() as conn:
        result = svc.list_profiles(conn)

    usernames = [p.username for p in result.profiles]
    assert usernames == ["alice", "bob", "zoe"]


def test_list_profiles_includes_total_steps_all_time():
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "alice",  "t": "alice_token______________________", "j": "2026-05-19T00:00:00"},
        ],
        steps=[
            {"u": 1, "ts": "2026-05-20T18:00:00", "t": 5000},
            {"u": 1, "ts": "2026-05-20T20:00:00", "t": 9000},
            {"u": 1, "ts": "2026-05-21T18:00:00", "t": 4000},
        ],
    )
    with engine.connect() as conn:
        result = svc.list_profiles(conn)

    assert len(result.profiles) == 1
    assert result.profiles[0].total_steps_all_time == 9000 + 4000


def test_list_profiles_zero_step_users_show_zero_total():
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "newbie", "t": "newbie_token_____________________", "j": "2026-05-25T00:00:00"},
        ],
        steps=[],
    )
    with engine.connect() as conn:
        result = svc.list_profiles(conn)

    assert result.profiles[0].total_steps_all_time == 0


def test_list_profiles_returns_empty_list_for_empty_db():
    engine = _engine_with(profiles=[], steps=[])
    with engine.connect() as conn:
        result = svc.list_profiles(conn)

    assert result.profiles == []


from fastapi.testclient import TestClient

from backend.app import db, main


def test_route_get_profiles_returns_200_alphabetical(monkeypatch):
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "zoe",   "t": "zoe_token________________________", "j": "2026-05-20T00:00:00"},
            {"id": 2, "u": "alice", "t": "alice_token______________________", "j": "2026-05-19T00:00:00"},
        ],
        steps=[],
    )
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/profiles")
    assert response.status_code == 200
    body = response.json()
    assert [p["username"] for p in body["profiles"]] == ["alice", "zoe"]


def test_route_get_profiles_includes_total_steps(monkeypatch):
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "alice", "t": "alice_token______________________", "j": "2026-05-19T00:00:00"},
        ],
        steps=[
            {"u": 1, "ts": "2026-05-20T18:00:00", "t": 9000},
        ],
    )
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/profiles")
    body = response.json()
    assert body["profiles"][0]["total_steps_all_time"] == 9000


def test_route_get_profiles_maps_totals_to_correct_users(monkeypatch):
    """Two users with different totals — each row must show its own
    total, not a mixed-up or off-by-one association."""
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "alice", "t": "alice_token______________________", "j": "2026-05-19T00:00:00"},
            {"id": 2, "u": "bob",   "t": "bob_token________________________",   "j": "2026-05-20T00:00:00"},
        ],
        steps=[
            {"u": 1, "ts": "2026-05-20T18:00:00", "t": 9000},
            {"u": 2, "ts": "2026-05-20T18:00:00", "t": 3000},
        ],
    )
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/profiles")
    body = response.json()
    by_username = {p["username"]: p["total_steps_all_time"] for p in body["profiles"]}
    assert by_username == {"alice": 9000, "bob": 3000}
