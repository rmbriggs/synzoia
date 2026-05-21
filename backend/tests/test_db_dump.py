from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


def _sqlite_engine_with_v1_schema():
    """In-memory SQLite engine with all 5 v1 tables. Columns are simplified
    (TEXT for everything) since SQLite doesn't have Postgres types — but
    SELECT * still returns the inserted shape, which is what we care about."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE profiles (id text, display_name text, timezone text)"
            )
        )
        conn.execute(text("CREATE TABLE groups (id text, name text, invite_code text)"))
        conn.execute(
            text("CREATE TABLE memberships (group_id text, user_id text)")
        )
        conn.execute(
            text(
                "CREATE TABLE sleep_posts ("
                "id text, user_id text, night_of text, duration_min integer)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE streaks ("
                "user_id text, current_streak integer, longest_streak integer)"
            )
        )
    return engine


def test_db_dump_returns_rows_keyed_by_table(monkeypatch):
    engine = _sqlite_engine_with_v1_schema()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO profiles (id, display_name, timezone) "
                "VALUES ('u1', 'Micah', 'America/Chicago')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO groups (id, name, invite_code) "
                "VALUES ('g1', 'Owls', 'ABCD1234')"
            )
        )
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/db/dump")

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 100
    assert body["tables"]["profiles"] == [
        {"id": "u1", "display_name": "Micah", "timezone": "America/Chicago"}
    ]
    assert body["tables"]["groups"] == [
        {"id": "g1", "name": "Owls", "invite_code": "ABCD1234"}
    ]
    assert body["tables"]["memberships"] == []
    assert body["tables"]["sleep_posts"] == []
    assert body["tables"]["streaks"] == []
    assert all(err is None for err in body["errors"].values())


def test_db_dump_reports_per_table_errors_when_table_missing(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Only `profiles` exists — the other 4 queries will raise.
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE profiles (id text)"))
        conn.execute(text("INSERT INTO profiles VALUES ('u1')"))
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/db/dump")

    assert response.status_code == 200
    body = response.json()
    assert body["tables"]["profiles"] == [{"id": "u1"}]
    assert body["tables"]["groups"] == []
    assert body["errors"]["profiles"] is None
    assert body["errors"]["groups"] is not None  # an exception class name
