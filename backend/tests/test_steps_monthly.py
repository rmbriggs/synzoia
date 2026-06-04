"""Tests for get_user_monthly service.

Uses in-memory SQLite via the same _engine_with_users helper pattern as
the rest of the steps test suite. Timestamps in fixtures are stored as
naive UTC (matching what psycopg sees from the Shortcut)."""

from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app.services import steps as svc
from backend.app import db, main
from fastapi.testclient import TestClient


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
        conn.execute(
            text(
                "INSERT INTO profiles (id, username, token) VALUES "
                "(1, 'alice', 'alice_token_aaaaaaaaaaaaaaaaa'), "
                "(2, 'bob', 'bob_token_bbbbbbbbbbbbbbbbbbb')"
            )
        )
    return engine


def test_get_user_monthly_returns_expected_shape():
    """Rolling 30-day window ending 2026-05-31 — Alice has one day with 9000 steps on the 23rd CT."""
    engine = _engine()
    with engine.begin() as conn:
        # UTC 2026-05-24T02:00 → CT 2026-05-23T21:00 → CT date 2026-05-23
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) "
                "VALUES (1, '2026-05-24T02:00:00', 9000)"
            )
        )

    with engine.connect() as conn:
        # as_of=2026-05-31 → rolling_bounds(30) = 2026-05-02..2026-05-31
        result = svc.get_user_monthly(conn, "alice", date(2026, 5, 31))

    assert result.username == "alice"
    assert result.month_start == date(2026, 5, 2)
    assert result.month_end == date(2026, 5, 31)
    assert result.monthly_total == 9000
    assert len(result.daily_breakdown) == 1
    assert result.daily_breakdown[0].date == date(2026, 5, 23)
    assert result.daily_breakdown[0].total == 9000


def test_get_user_monthly_returns_empty_breakdown_for_inactive_month():
    """A month the user had zero step writes returns empty list, not zeros."""
    engine = _engine()
    with engine.connect() as conn:
        result = svc.get_user_monthly(conn, "alice", date(2026, 4, 1))

    assert result.monthly_total == 0
    assert result.daily_breakdown == []


def test_get_user_monthly_buckets_by_ct_date_not_utc():
    """A 9k step row at 2026-05-01T02:30 UTC bucketed to CT 2026-04-30.
    With as_of=2026-05-31 the rolling window is 2026-05-02..2026-05-31,
    so the April 30 bucket must NOT count."""
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) "
                "VALUES (1, '2026-05-01T02:30:00', 9000)"
            )
        )

    with engine.connect() as conn:
        # as_of=2026-05-31 → window 2026-05-02..2026-05-31; 2026-04-30 excluded
        result = svc.get_user_monthly(conn, "alice", date(2026, 5, 31))

    assert result.monthly_total == 0


def test_get_user_monthly_rank_uses_dense_rank_within_month():
    """Alice 12000, Bob 8000 in rolling window → Alice #1, Bob #2."""
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) VALUES "
                "(1, '2026-05-15T18:00:00', 12000), "
                "(2, '2026-05-15T18:00:00', 8000)"
            )
        )

    with engine.connect() as conn:
        # as_of=2026-05-31 → window 2026-05-02..2026-05-31; both rows included
        alice = svc.get_user_monthly(conn, "alice", date(2026, 5, 31))
        bob = svc.get_user_monthly(conn, "bob", date(2026, 5, 31))

    assert alice.rank_this_month == 1
    assert bob.rank_this_month == 2


def test_get_user_monthly_unknown_user_raises_user_not_found():
    engine = _engine()
    with engine.connect() as conn:
        with pytest.raises(svc.UserNotFound) as excinfo:
            svc.get_user_monthly(conn, "ghost", date(2026, 5, 1))

    assert excinfo.value.username == "ghost"


def test_route_user_monthly_returns_200_and_correct_shape(monkeypatch):
    engine = _engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) "
                "VALUES (1, '2026-05-24T02:00:00', 9000)"
            )
        )

    # Rolling 30-day window ending 2026-05-31: start=2026-05-02..end=2026-05-31
    response = TestClient(main.app).get(
        "/api/steps/users/alice/monthly?as_of=2026-05-31"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["month_start"] == "2026-05-02"
    assert body["month_end"] == "2026-05-31"
    assert body["monthly_total"] == 9000
    assert body["rank_this_month"] == 1
    assert body["daily_breakdown"] == [
        {"date": "2026-05-23", "total": 9000}
    ]


def test_route_user_monthly_defaults_to_current_ct_month(monkeypatch):
    engine = _engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/steps/users/alice/monthly")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert "month_start" in body and "month_end" in body
    assert body["monthly_total"] == 0


def test_route_user_monthly_returns_404_for_unknown_user(monkeypatch):
    engine = _engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get(
        "/api/steps/users/ghost/monthly?as_of=2026-05-31"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"
