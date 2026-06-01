"""HTTP-level tests for POST /api/workouts/run + /api/workouts/calories.

Covers:
- Auth (Bearer required, bad token → 401)
- Happy paths for both kinds — row lands with correct kind + metrics
- Overlap dedup — re-posting the same window of the same kind merges
- Different kinds at the same time stay independent
- ended_at <= started_at → 422
- user_id in body is ignored
- Missing required field for the kind (no distance_m for /run, no
  active_calories for /calories) → 422 from Pydantic
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


ALICE_TOKEN = "ALCE-AAAA-AAAA-AAAA"
BOB_TOKEN = "BOBB-BBBB-BBBB-BBBB"


def _engine_with_users():
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
                "CREATE TABLE workouts ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "workout_kind text not null, "
                "started_at text not null, "
                "ended_at text not null, "
                "duration_min integer not null, "
                "distance_m integer, "
                "active_calories integer, "
                "avg_heart_rate integer, "
                "max_heart_rate integer, "
                "captured_at text not null default (datetime('now')), "
                "created_at text not null default (datetime('now')))"
            )
        )
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) "
                "VALUES (:u, :t, :j)"
            ),
            [
                {"u": "alice", "t": ALICE_TOKEN, "j": "2026-05-01T00:00:00"},
                {"u": "bob", "t": BOB_TOKEN, "j": "2026-05-01T00:00:00"},
            ],
        )
    return engine


def _count_workouts(engine, user_id=None, kind=None) -> int:
    sql = "SELECT count(*) FROM workouts"
    params: dict = {}
    clauses: list[str] = []
    if user_id is not None:
        clauses.append("user_id = :uid")
        params["uid"] = user_id
    if kind is not None:
        clauses.append("workout_kind = :kind")
        params["kind"] = kind
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    with engine.connect() as conn:
        return int(conn.execute(text(sql), params).scalar() or 0)


def _run_payload(**overrides) -> dict:
    base = {
        "started_at": "2026-05-25T07:00:00",
        "ended_at": "2026-05-25T07:35:00",
        "distance_m": 5000,
        "active_calories": 320,
        "avg_heart_rate": 145,
        "max_heart_rate": 172,
    }
    base.update(overrides)
    return base


def _calories_payload(**overrides) -> dict:
    base = {
        "started_at": "2026-05-25T18:00:00",
        "ended_at": "2026-05-25T18:45:00",
        "active_calories": 280,
        "avg_heart_rate": 130,
        "max_heart_rate": 158,
    }
    base.update(overrides)
    return base


# ----- Auth ---------------------------------------------------------------


def test_run_without_auth_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    r = TestClient(main.app).post("/api/workouts/run", json=_run_payload())

    assert r.status_code == 401
    assert _count_workouts(engine) == 0


def test_calories_without_auth_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    r = TestClient(main.app).post(
        "/api/workouts/calories", json=_calories_payload()
    )

    assert r.status_code == 401
    assert _count_workouts(engine) == 0


# ----- Happy paths --------------------------------------------------------


def test_run_creates_row_with_distance(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=_run_payload(),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["user_id"] == 1
    assert body["workout_kind"] == "run"
    assert body["distance_m"] == 5000
    assert body["duration_min"] == 35
    assert body["avg_heart_rate"] == 145
    assert _count_workouts(engine, user_id=1, kind="run") == 1


def test_calories_creates_row(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    r = TestClient(main.app).post(
        "/api/workouts/calories",
        json=_calories_payload(),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["workout_kind"] == "calories"
    assert body["active_calories"] == 280
    assert body["duration_min"] == 45
    assert _count_workouts(engine, user_id=1, kind="calories") == 1


# ----- Overlap dedup ------------------------------------------------------


def test_reposting_same_run_window_updates_existing_row(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    first = client.post("/api/workouts/run", json=_run_payload(), headers=headers)
    assert first.status_code == 201

    # Same window, slightly more complete (longer end + more distance) —
    # should MERGE into the existing row, not create a second.
    second = client.post(
        "/api/workouts/run",
        json=_run_payload(ended_at="2026-05-25T07:40:00", distance_m=5500),
        headers=headers,
    )
    assert second.status_code == 201
    assert second.json()["distance_m"] == 5500
    assert second.json()["duration_min"] == 40
    assert _count_workouts(engine, user_id=1, kind="run") == 1


def test_run_and_calories_at_same_time_are_independent_rows(monkeypatch):
    """Different kinds shouldn't dedupe to each other even if they
    overlap in time — they're distinct activities."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    client.post("/api/workouts/run", json=_run_payload(), headers=headers)
    client.post(
        "/api/workouts/calories",
        json=_calories_payload(
            started_at="2026-05-25T07:00:00",  # exact same window
            ended_at="2026-05-25T07:35:00",
        ),
        headers=headers,
    )

    assert _count_workouts(engine, user_id=1) == 2
    assert _count_workouts(engine, user_id=1, kind="run") == 1
    assert _count_workouts(engine, user_id=1, kind="calories") == 1


# ----- Validation ---------------------------------------------------------


def test_run_with_ended_before_started_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=_run_payload(
            started_at="2026-05-25T08:00:00",
            ended_at="2026-05-25T07:00:00",
        ),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 422
    assert _count_workouts(engine) == 0


def test_run_missing_distance_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = _run_payload()
    del payload["distance_m"]

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 422
    assert _count_workouts(engine) == 0


def test_calories_missing_calories_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = _calories_payload()
    del payload["active_calories"]

    r = TestClient(main.app).post(
        "/api/workouts/calories",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 422
    assert _count_workouts(engine) == 0


def test_user_id_in_body_is_ignored(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = _run_payload()
    payload["user_id"] = 999  # malicious — dropped by Pydantic

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201
    assert r.json()["user_id"] == 1  # alice
    assert _count_workouts(engine, user_id=1) == 1
    assert _count_workouts(engine, user_id=999) == 0
