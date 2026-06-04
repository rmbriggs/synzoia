from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app import db, main
from backend.tests.schema import make_engine


# Bearer token corresponding to the seeded profile. Tests send this
# in the Authorization header; the require_user dependency resolves
# it to user_id=1.
SEED_TOKEN = "MIC0-HAYY-HAYY-HAYY"


def _sqlite_engine_with_live_schema():
    """In-memory SQLite engine matching the post-0003 + post-0004 schema
    (profiles + steps). Columns are simplified since SQLite doesn't have
    Postgres types — but SELECT * still returns the inserted shape."""
    engine = make_engine("profiles", "steps")
    return engine


def _seed_profile(engine, token: str = SEED_TOKEN) -> None:
    """Insert a profile whose token the tests can present in the
    Authorization header. Some tests intentionally skip this when
    asserting the unauthenticated path."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) "
                "VALUES (:u, :t, :j)"
            ),
            {"u": "micah", "t": token, "j": "2026-05-23T00:00:00Z"},
        )


def _auth() -> dict:
    return {"Authorization": f"Bearer {SEED_TOKEN}"}


def test_db_dump_without_auth_returns_401(monkeypatch):
    """/api/db/dump used to be world-readable, which leaked every
    user's profiles.token (the auth credential). Now it requires a
    Bearer token like any other write/admin endpoint."""
    engine = _sqlite_engine_with_live_schema()
    _seed_profile(engine)
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/db/dump")

    assert response.status_code == 401


def test_db_dump_returns_rows_keyed_by_table(monkeypatch):
    engine = _sqlite_engine_with_live_schema()
    _seed_profile(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) "
                "VALUES (1, '2026-05-23T08:00:00Z', 1234)"
            )
        )
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/db/dump", headers=_auth())

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 100
    # `token` column is redacted out of the profiles dump — even an
    # authed user must not see another user's credential.
    assert body["tables"]["profiles"] == [
        {
            "id": 1,
            "username": "micah",
            "join_date": "2026-05-23T00:00:00Z",
        }
    ]
    assert body["tables"]["steps"] == [
        {
            "id": 1,
            "user_id": 1,
            "timestamp": "2026-05-23T08:00:00Z",
            "total": 1234,
        }
    ]
    assert body["errors"]["profiles"] is None
    assert body["errors"]["steps"] is None


def test_db_dump_never_returns_token_column(monkeypatch):
    """Belt-and-suspenders for the credential-leak fix: confirm no row
    in the dump carries a `token` key, regardless of how many profiles
    exist."""
    engine = _sqlite_engine_with_live_schema()
    _seed_profile(engine, token=SEED_TOKEN)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) "
                "VALUES ('angela', 'AAAA-BBBB-CCCC-DDDD', '2026-05-24T00:00:00Z')"
            )
        )
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/db/dump", headers=_auth())

    assert response.status_code == 200
    profiles = response.json()["tables"]["profiles"]
    assert len(profiles) == 2
    for row in profiles:
        assert "token" not in row
        # And paranoid string-level check in case a future bug leaks
        # tokens through a different column name:
        assert SEED_TOKEN not in str(row)
        assert "AAAA-BBBB-CCCC-DDDD" not in str(row)


def test_db_dump_reports_per_table_errors_when_table_missing(monkeypatch):
    """When the profiles table is missing entirely, auth itself fails
    (the token lookup raises) — so this endpoint can't be reached. To
    exercise the per-table error branch we keep profiles but drop the
    other v1 tables."""
    engine = make_engine("profiles")
    _seed_profile(engine)
    # `steps`, `posts`, `sleep` intentionally missing — those queries
    # will raise per-table.
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/db/dump", headers=_auth())

    assert response.status_code == 200
    body = response.json()
    # profiles exists, so it returns rows (one — the seeded auth user).
    assert len(body["tables"]["profiles"]) == 1
    assert body["errors"]["profiles"] is None
    # Other v1 tables are missing → per-table errors recorded.
    for missing in ("steps", "posts", "sleep"):
        assert body["tables"][missing] == []
        assert body["errors"][missing] is not None
