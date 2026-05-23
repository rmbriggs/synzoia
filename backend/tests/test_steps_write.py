"""HTTP-level tests for POST /api/steps + Bearer-token auth.

The write path resolves `user_id` from the `Authorization: Bearer
<token>` header. These tests exercise the wire: valid token inserts
a row, missing/bad token returns 401 with no row written, and the
inserted row is owned by the right user (never spoofable via body).
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


ALICE_TOKEN = "alice_token_aaaaaaaaaaaaaaaaaaaaaaaa"
BOB_TOKEN = "bob_token_bbbbbbbbbbbbbbbbbbbbbbbbbbbb"


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
                "CREATE TABLE steps ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "timestamp text not null, "
                "total integer not null)"
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


def _count_steps(engine, user_id: int) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                text("SELECT count(*) FROM steps WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar()
            or 0
        )


def test_post_steps_inserts_row_for_token_owner(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T08:00:00", "total": 8432},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == 1  # alice
    assert body["total"] == 8432
    assert body["timestamp"].startswith("2026-05-23T08:00:00")
    assert isinstance(body["id"], int)

    # Row landed in DB under alice.
    assert _count_steps(engine, user_id=1) == 1
    assert _count_steps(engine, user_id=2) == 0


def test_post_steps_without_auth_header_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T08:00:00", "total": 8432},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    assert _count_steps(engine, user_id=1) == 0


def test_post_steps_with_bad_token_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T08:00:00", "total": 8432},
        headers={"Authorization": "Bearer not_a_real_token"},
    )

    assert response.status_code == 401
    assert _count_steps(engine, user_id=1) == 0


def test_post_steps_with_malformed_auth_header_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # "Token x" instead of "Bearer x" — also no scheme at all.
    for header in ["Token abc", ALICE_TOKEN, "Bearer "]:
        response = TestClient(main.app).post(
            "/api/steps",
            json={"timestamp": "2026-05-23T08:00:00", "total": 8432},
            headers={"Authorization": header},
        )
        assert response.status_code == 401, header

    assert _count_steps(engine, user_id=1) == 0


def test_post_steps_user_id_is_resolved_from_token_not_body(monkeypatch):
    """Even if a malicious client sends a `user_id` in the JSON body,
    the row must be written under the token-resolved user. This guards
    the CLAUDE.md rule: user_id from JWT, never from request body."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={
            "timestamp": "2026-05-23T08:00:00",
            "total": 8432,
            "user_id": 2,  # bob — should be ignored
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == 1  # alice, from the token
    assert _count_steps(engine, user_id=1) == 1
    assert _count_steps(engine, user_id=2) == 0


def test_post_steps_with_negative_total_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T08:00:00", "total": -50},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 422
    assert _count_steps(engine, user_id=1) == 0
