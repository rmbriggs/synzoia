"""Tests for POST /api/profiles (sign-up endpoint).

The endpoint runs against Postgres in production (BIGSERIAL id, timestamptz
join_date). For unit tests we monkeypatch the engine to an in-memory SQLite
db with a profiles table that has the same column NAMES; the column types
diverge but the endpoint only RETURNINGs username/token/join_date, which
SQLite is happy to round-trip as strings.
"""

import re

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


def _profiles_engine():
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
    return engine


def test_create_profile_returns_username_token_and_join_date(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    response = client.post("/api/profiles", json={"username": "micah"})

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "micah"
    # 32 hex chars (secrets.token_hex(16)).
    assert re.fullmatch(r"[0-9a-f]{32}", body["token"])
    assert body["join_date"]  # populated by the DB default


def test_create_profile_409s_on_duplicate_username(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    first = client.post("/api/profiles", json={"username": "micah"})
    assert first.status_code == 201

    second = client.post("/api/profiles", json={"username": "micah"})
    assert second.status_code == 409
    assert second.json() == {
        "error": {
            "code": "username_taken",
            "message": "That username is already taken.",
        }
    }


def test_create_profile_422s_on_invalid_chars(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    response = client.post("/api/profiles", json={"username": "micah!"})

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_username",
            "message": (
                "Username must be 1-30 characters of letters, digits, or underscore."
            ),
        }
    }


def test_create_profile_422s_on_empty_username(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    # Pydantic catches min_length=1 before our regex; either is fine
    # as long as it's a 422.
    response = client.post("/api/profiles", json={"username": ""})

    assert response.status_code == 422


def test_create_profile_422s_on_too_long_username(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    response = client.post("/api/profiles", json={"username": "a" * 31})

    assert response.status_code == 422


def test_two_different_usernames_get_different_tokens(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    a = client.post("/api/profiles", json={"username": "alice"}).json()
    b = client.post("/api/profiles", json={"username": "bob"}).json()

    assert a["token"] != b["token"]
