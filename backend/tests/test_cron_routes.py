"""HTTP-level tests for /api/cron/daily-recap.

Exercises the wire: secret-authed write of a leaderboard_recap post
for yesterday's top 3, idempotency when called twice, the no-data
short-circuit, and the 401 path for missing/wrong auth."""

import json
import os

from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app import db, main
from backend.tests.schema import make_engine


CRON_SECRET = "test_cron_secret_value"


def _engine_with_yesterday_data(seed_rows=True):
    engine = make_engine("profiles", "steps", "posts")
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) "
                "VALUES ('micah', 'tm', '2026-05-01T00:00:00'), "
                "('angela', 'ta', '2026-05-01T00:00:00'), "
                "('bob', 'tb', '2026-05-01T00:00:00')"
            )
        )
        if seed_rows:
            # Yesterday CT = 2026-05-22 (we pin today_ct = 2026-05-23).
            # Timestamps stored as UTC and bucketed to CT via _ct_date.
            # UTC afternoon = CT morning of the same day.
            conn.execute(
                text(
                    "INSERT INTO steps (user_id, timestamp, total) VALUES "
                    "(1, '2026-05-22T18:00:00', 12000), "
                    "(2, '2026-05-22T18:00:00', 9500), "
                    "(3, '2026-05-22T18:00:00', 4200)"
                )
            )
    return engine


def _post_rows(engine, type_filter=None):
    with engine.connect() as conn:
        if type_filter:
            return list(
                conn.execute(
                    text(
                        "SELECT id, type, body, details FROM posts "
                        "WHERE type = :t ORDER BY id ASC"
                    ),
                    {"t": type_filter},
                )
                .mappings()
                .all()
            )
        return list(
            conn.execute(text("SELECT id, type FROM posts ORDER BY id ASC"))
            .mappings()
            .all()
        )


def test_daily_recap_inserts_top3_for_yesterday(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    engine = _engine_with_yesterday_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    from backend.app.routes import cron as cron_routes
    from datetime import date

    monkeypatch.setattr(cron_routes, "_today_ct", lambda: date(2026, 5, 23))

    response = TestClient(main.app).get(
        "/api/cron/daily-recap",
        headers={"Authorization": f"Bearer {CRON_SECRET}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "inserted" in body

    rows = _post_rows(engine, type_filter="leaderboard_recap")
    assert len(rows) == 1
    details = json.loads(rows[0]["details"])
    assert details["date"] == "2026-05-22"
    assert [t["username"] for t in details["top"]] == ["micah", "angela", "bob"]
    assert [t["total"] for t in details["top"]] == [12000, 9500, 4200]
    assert rows[0]["body"] == "Yesterday's top 3"


def test_daily_recap_skipped_when_no_data(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    engine = _engine_with_yesterday_data(seed_rows=False)
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    from backend.app.routes import cron as cron_routes
    from datetime import date

    monkeypatch.setattr(cron_routes, "_today_ct", lambda: date(2026, 5, 23))

    response = TestClient(main.app).get(
        "/api/cron/daily-recap",
        headers={"Authorization": f"Bearer {CRON_SECRET}"},
    )

    assert response.status_code == 200
    assert response.json() == {"skipped": "no_data"}
    assert _post_rows(engine, type_filter="leaderboard_recap") == []


def test_daily_recap_idempotent_on_second_call(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    engine = _engine_with_yesterday_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    from backend.app.routes import cron as cron_routes
    from datetime import date

    monkeypatch.setattr(cron_routes, "_today_ct", lambda: date(2026, 5, 23))
    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {CRON_SECRET}"}

    first = client.get("/api/cron/daily-recap", headers=headers)
    second = client.get("/api/cron/daily-recap", headers=headers)

    assert first.status_code == 200 and "inserted" in first.json()
    assert second.status_code == 200
    assert second.json() == {"skipped": "already_posted"}
    assert len(_post_rows(engine, type_filter="leaderboard_recap")) == 1


def test_daily_recap_rejects_missing_or_bad_auth(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    engine = _engine_with_yesterday_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    r1 = client.get("/api/cron/daily-recap")
    r2 = client.get(
        "/api/cron/daily-recap", headers={"Authorization": "Bearer wrong"}
    )

    assert r1.status_code == 401
    assert r2.status_code == 401
    assert _post_rows(engine, type_filter="leaderboard_recap") == []


def test_daily_recap_503s_when_cron_secret_not_configured(monkeypatch):
    """If the backend itself has no CRON_SECRET env var (mis-deploy),
    the endpoint refuses with 503 rather than silently allowing
    unauthenticated cron triggers."""
    monkeypatch.delenv("CRON_SECRET", raising=False)
    engine = _engine_with_yesterday_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get(
        "/api/cron/daily-recap",
        headers={"Authorization": "Bearer anything"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "cron_misconfigured"
    assert _post_rows(engine, type_filter="leaderboard_recap") == []
