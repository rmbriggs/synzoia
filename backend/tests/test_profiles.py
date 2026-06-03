"""Tests for POST /api/profiles (sign-up endpoint, post-C2).

The endpoint now requires a Supabase Auth JWT in the Authorization
header — anonymous signup is not allowed. Tests mint short-lived
JWTs against a known SUPABASE_JWT_SECRET and present them as if
they came from Supabase's `auth.users` flow.

In production the schema is Postgres (BIGSERIAL id, UUID
supabase_user_id, timestamptz join_date). For unit tests we
monkeypatch the engine to in-memory SQLite with the same column
NAMES; the column types diverge but the endpoint only RETURNINGs
username/token/join_date, which SQLite round-trips as strings.
"""

import os
import re
import uuid

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


# Test-only Supabase JWT secret. The auth module reads this from the
# env var at JWT-verification time, so setting it here (via the
# `_jwt_secret` fixture) is enough to make signed-locally tokens
# round-trip correctly.
_TEST_JWT_SECRET = "test-jwt-secret-not-used-anywhere-real"


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    """Inject a deterministic SUPABASE_JWT_SECRET so test JWTs the
    helpers below mint will verify against the auth module's check."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", _TEST_JWT_SECRET)


def _mint_jwt(supabase_uid: str | None = None) -> str:
    """Produce a Supabase-shaped JWT (HS256, audience='authenticated')
    signed with the test secret. `sub` is a fresh UUID by default so
    each call simulates a different Supabase user signing up."""
    sub = supabase_uid or str(uuid.uuid4())
    return jwt.encode(
        {"sub": sub, "aud": "authenticated"},
        _TEST_JWT_SECRET,
        algorithm="HS256",
    )


def _auth_headers(jwt_token: str) -> dict:
    return {"Authorization": f"Bearer {jwt_token}"}


def _profiles_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        # supabase_user_id is added by migration 0012 — mirror it
        # here so the INSERT statement in routes/profiles.py finds
        # the column.
        conn.execute(
            text(
                "CREATE TABLE profiles ("
                "id integer primary key autoincrement, "
                "username text not null unique, "
                "token text not null unique, "
                "supabase_user_id text unique, "
                "join_date text not null default (datetime('now')))"
            )
        )
    return engine


def test_create_profile_returns_username_token_and_join_date(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    response = client.post(
        "/api/profiles",
        json={"username": "micah"},
        headers=_auth_headers(_mint_jwt()),
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["username"] == "micah"
    # 4 groups of 4 uppercase letters joined by dashes (XXXX-XXXX-XXXX-XXXX).
    assert re.fullmatch(r"[A-Z]{4}-[A-Z]{4}-[A-Z]{4}-[A-Z]{4}", body["token"])
    assert body["join_date"]  # populated by the DB default


def test_create_profile_without_jwt_returns_401(monkeypatch):
    """Pre-C2 the signup endpoint was anonymous — anyone could squat
    usernames or burn DB rows. Confirm the JWT requirement is real."""
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    response = client.post("/api/profiles", json={"username": "micah"})

    assert response.status_code == 401


def test_create_profile_with_bad_jwt_returns_401(monkeypatch):
    """A token that ISN'T signed by us must be rejected — that's the
    whole point of cryptographic verification."""
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    bad_jwt = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated"},
        "wrong-secret",
        algorithm="HS256",
    )
    response = client.post(
        "/api/profiles",
        json={"username": "micah"},
        headers=_auth_headers(bad_jwt),
    )

    assert response.status_code == 401


def test_create_profile_409s_on_duplicate_username(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    # Two distinct Supabase users, same desired username — second
    # one should lose the race to the unique constraint.
    first = client.post(
        "/api/profiles",
        json={"username": "micah"},
        headers=_auth_headers(_mint_jwt()),
    )
    assert first.status_code == 201

    second = client.post(
        "/api/profiles",
        json={"username": "micah"},
        headers=_auth_headers(_mint_jwt()),
    )
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

    response = client.post(
        "/api/profiles",
        json={"username": "micah!"},
        headers=_auth_headers(_mint_jwt()),
    )

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

    response = client.post(
        "/api/profiles",
        json={"username": ""},
        headers=_auth_headers(_mint_jwt()),
    )

    assert response.status_code == 422


def test_create_profile_422s_on_too_long_username(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    response = client.post(
        "/api/profiles",
        json={"username": "a" * 31},
        headers=_auth_headers(_mint_jwt()),
    )

    assert response.status_code == 422


def test_two_different_usernames_get_different_tokens(monkeypatch):
    engine = _profiles_engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    a = client.post(
        "/api/profiles",
        json={"username": "alice"},
        headers=_auth_headers(_mint_jwt()),
    ).json()
    b = client.post(
        "/api/profiles",
        json={"username": "bob"},
        headers=_auth_headers(_mint_jwt()),
    ).json()

    assert a["token"] != b["token"]
