"""HTTP-level tests for POST /api/sleep + Bearer-token auth.

The write path:
- Resolves `user_id` from the `Authorization: Bearer <token>` header.
- Accepts Angela's iOS Shortcut payload (camelCase keys, hours as
  decimal): `FallAsleepTime`, `WakeUpTime`, `TotalSleepTimeHr`.
- Converts hours → minutes server-side and stores integer minutes
  in `duration_min`.
- Computes `night_of` server-side from wake_time's CT date minus 1
  day (NEVER trusted from the body).

These tests exercise the wire: valid token inserts a row, missing/bad
token returns 401, the row is owned by the right user (never
spoofable via body), duplicate nights return 409, malformed payloads
return 422.
"""

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
                "INSERT INTO profiles (username, token, join_date) "
                "VALUES (:u, :t, :j)"
            ),
            [
                {"u": "alice", "t": ALICE_TOKEN, "j": "2026-05-01T00:00:00"},
                {"u": "bob", "t": BOB_TOKEN, "j": "2026-05-01T00:00:00"},
            ],
        )
    return engine


def _count_sleep(engine, user_id=None) -> int:
    with engine.connect() as conn:
        if user_id is None:
            return int(
                conn.execute(text("SELECT count(*) FROM sleep")).scalar() or 0
            )
        return int(
            conn.execute(
                text("SELECT count(*) FROM sleep WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar()
            or 0
        )


# Default Shortcut-shaped payload (camelCase keys, hours).
def _payload(**overrides):
    base = {
        "FallAsleepTime": "2026-05-23T03:00:00",
        "WakeUpTime": "2026-05-23T11:00:00",
        "TotalSleepTimeHr": 7.5,  # 7.5h → 450 min
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_post_sleep_inserts_row_for_token_owner(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json={
            **_payload(),
            "rem_minutes": 95,
            "core_minutes": 240,
            "deep_minutes": 85,
            "awake_minutes": 40,
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == 1  # alice
    # 7.5 hours → 450 minutes (round)
    assert body["duration_min"] == 450
    assert body["rem_minutes"] == 95
    # night_of = wake_time's CT date − 1 day.
    # 2026-05-23T11:00:00 (naive UTC) → 06:00 CT on 2026-05-23
    # → wake_date = 2026-05-23, night_of = 2026-05-22
    assert body["night_of"] == "2026-05-22"
    assert _count_sleep(engine, user_id=1) == 1


def test_post_sleep_accepts_snake_case_aliases_too(monkeypatch):
    """For curl-from-terminal sanity, accept bedtime/wake_time/
    total_sleep_hours as well (populate_by_name=True on the model).
    The Shortcut uses camelCase; CLIs and tests can use snake_case."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json={
            "bedtime": "2026-05-23T03:00:00",
            "wake_time": "2026-05-23T11:00:00",
            "total_sleep_hours": 7.5,
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    assert response.json()["duration_min"] == 450


def test_post_sleep_without_auth_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post("/api/sleep", json=_payload())

    assert response.status_code == 401
    assert _count_sleep(engine) == 0


def test_post_sleep_with_bad_token_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json=_payload(),
        headers={"Authorization": "Bearer not_a_real_token"},
    )

    assert response.status_code == 401
    assert _count_sleep(engine) == 0


# ---------------------------------------------------------------------------
# Body validation
# ---------------------------------------------------------------------------


def test_post_sleep_with_wake_before_bed_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json=_payload(
            FallAsleepTime="2026-05-23T11:00:00",
            WakeUpTime="2026-05-23T03:00:00",
        ),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 422
    assert _count_sleep(engine) == 0


def test_post_sleep_with_negative_hours_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json=_payload(TotalSleepTimeHr=-0.5),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 422
    assert _count_sleep(engine) == 0


def test_post_sleep_with_implausible_hours_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # 25 hours — above the 24-hour Field cap on TotalSleepTimeHr.
    response = TestClient(main.app).post(
        "/api/sleep",
        json=_payload(
            WakeUpTime="2026-05-24T04:00:00",
            TotalSleepTimeHr=25,
        ),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 422
    assert _count_sleep(engine) == 0


# ---------------------------------------------------------------------------
# Anti-spoofing + idempotency
# ---------------------------------------------------------------------------


def test_post_sleep_user_id_is_resolved_from_token_not_body(monkeypatch):
    """Malicious body sends user_id=2 (bob). Row must still land
    under alice because she owns the token."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json={**_payload(), "user_id": 2},  # ignored
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == 1
    assert _count_sleep(engine, user_id=1) == 1
    assert _count_sleep(engine, user_id=2) == 0


def test_post_sleep_night_of_is_not_trusted_from_body(monkeypatch):
    """A client sending night_of in the body should NOT be able to
    pick a date; the service computes it from wake_time."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json={**_payload(), "night_of": "1999-01-01"},  # ignored
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    assert response.json()["night_of"] != "1999-01-01"


def test_post_sleep_duplicate_night_returns_409(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    first = client.post("/api/sleep", json=_payload(), headers=headers)
    assert first.status_code == 201

    second = client.post("/api/sleep", json=_payload(), headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "sleep_already_posted"

    assert _count_sleep(engine, user_id=1) == 1
