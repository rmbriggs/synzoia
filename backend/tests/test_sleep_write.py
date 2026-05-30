"""HTTP-level tests for POST /api/sleep + Bearer-token auth.

The write path resolves `user_id` from the `Authorization: Bearer
<token>` header and computes `night_of` server-side from wake_time's
CT date minus 1 day. These tests exercise the wire: valid token
inserts a row, missing/bad token returns 401, the row is owned by
the right user (never spoofable via body), duplicate nights return
409, malformed timestamps return 422.
"""

import json

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
                "CREATE TABLE posts ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "username text not null, "
                "type text not null, "
                "timestamp text not null, "
                "details text, "
                "body text)"
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


def _count_posts(engine) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(text("SELECT count(*) FROM posts")).scalar() or 0
        )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_post_sleep_inserts_row_for_token_owner(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json={
            "bedtime": "2026-05-23T03:00:00",
            "wake_time": "2026-05-23T11:00:00",
            "duration_min": 460,
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
    assert body["duration_min"] == 460
    assert body["rem_minutes"] == 95
    # 2026-05-23 03:00 UTC → 2026-05-22 22:00 CT → wake_date = 2026-05-22
    # night_of = wake_date − 1 = 2026-05-21
    # (wake_time 11:00 UTC → 06:00 CT on 2026-05-23 → wake_date = 2026-05-23
    #  night_of = 2026-05-22 — but service uses wake_time, so we check that)
    # Using the actual rule: night_of = CT(wake_time)::date - 1 day
    # CT(2026-05-23T11:00:00Z) = 2026-05-23 06:00 CT → date 2026-05-23
    # night_of = 2026-05-22
    assert body["night_of"] == "2026-05-22"
    assert _count_sleep(engine, user_id=1) == 1


def test_post_sleep_without_auth_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json={
            "bedtime": "2026-05-23T03:00:00",
            "wake_time": "2026-05-23T11:00:00",
            "duration_min": 460,
        },
    )

    assert response.status_code == 401
    assert _count_sleep(engine) == 0


def test_post_sleep_with_bad_token_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json={
            "bedtime": "2026-05-23T03:00:00",
            "wake_time": "2026-05-23T11:00:00",
            "duration_min": 460,
        },
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
        json={
            "bedtime": "2026-05-23T11:00:00",
            "wake_time": "2026-05-23T03:00:00",
            "duration_min": 460,
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 422
    assert _count_sleep(engine) == 0


def test_post_sleep_with_negative_duration_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json={
            "bedtime": "2026-05-23T03:00:00",
            "wake_time": "2026-05-23T11:00:00",
            "duration_min": -10,
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 422
    assert _count_sleep(engine) == 0


def test_post_sleep_with_implausible_duration_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # 1500 minutes = 25 hours, above the 24-hour Pydantic Field cap.
    response = TestClient(main.app).post(
        "/api/sleep",
        json={
            "bedtime": "2026-05-23T03:00:00",
            "wake_time": "2026-05-24T04:00:00",
            "duration_min": 1500,
        },
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
        json={
            "bedtime": "2026-05-23T03:00:00",
            "wake_time": "2026-05-23T11:00:00",
            "duration_min": 460,
            "user_id": 2,  # ignored
        },
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
        json={
            "bedtime": "2026-05-23T03:00:00",
            "wake_time": "2026-05-23T11:00:00",
            "duration_min": 460,
            "night_of": "1999-01-01",  # ignored
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    assert response.json()["night_of"] != "1999-01-01"


def test_post_sleep_duplicate_night_returns_409(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    payload = {
        "bedtime": "2026-05-23T03:00:00",
        "wake_time": "2026-05-23T11:00:00",
        "duration_min": 460,
    }
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    first = client.post("/api/sleep", json=payload, headers=headers)
    assert first.status_code == 201

    second = client.post("/api/sleep", json=payload, headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "sleep_already_posted"

    assert _count_sleep(engine, user_id=1) == 1


def test_post_sleep_creates_feed_post(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    resp = TestClient(main.app).post(
        "/api/sleep",
        json={
            "bedtime": "2026-05-28T05:00:00",
            "wake_time": "2026-05-28T12:32:00",
            "duration_min": 452,
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )
    assert resp.status_code == 201, resp.text

    with engine.connect() as conn:
        post = (
            conn.execute(
                text(
                    "SELECT username, type, timestamp, details, body "
                    "FROM posts"
                )
            )
            .mappings()
            .one()
        )
        sleep_night = conn.execute(
            text("SELECT night_of FROM sleep")
        ).scalar()

    assert post["username"] == "alice"
    assert post["type"] == "sleep"
    assert post["body"] == "slept 7h 32m"
    details = json.loads(post["details"])
    assert details["duration_min"] == 452
    assert details["night_of"] == sleep_night
    # Post timestamp anchors to wake_time so morning syncs land on top.
    assert "2026-05-28T12:32:00" in post["timestamp"]


def test_duplicate_night_creates_no_second_post(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)
    body = {
        "bedtime": "2026-05-28T05:00:00",
        "wake_time": "2026-05-28T12:32:00",
        "duration_min": 452,
    }
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    first = client.post("/api/sleep", json=body, headers=headers)
    assert first.status_code == 201
    second = client.post("/api/sleep", json=body, headers=headers)
    assert second.status_code == 409

    # The duplicate night rolled back — exactly one post, one sleep row.
    assert _count_posts(engine) == 1
    assert _count_sleep(engine) == 1
