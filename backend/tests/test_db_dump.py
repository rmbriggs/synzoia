from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


def _sqlite_engine_with_live_schema():
    """In-memory SQLite engine matching the post-0003 + post-0004 schema
    (profiles + steps). Columns are simplified since SQLite doesn't have
    Postgres types — but SELECT * still returns the inserted shape."""
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
                "username text, token text, join_date text)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE steps ("
                "id integer primary key autoincrement, "
                "user_id integer, timestamp text, total integer)"
            )
        )
    return engine


def test_db_dump_returns_rows_keyed_by_table(monkeypatch):
    engine = _sqlite_engine_with_live_schema()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) "
                "VALUES ('micah', 'deadbeef' || '00000000' || '00000000' || '00000000', "
                "'2026-05-23T00:00:00Z')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) "
                "VALUES (1, '2026-05-23T08:00:00Z', 1234)"
            )
        )
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/db/dump")

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 100
    assert body["tables"]["profiles"] == [
        {
            "id": 1,
            "username": "micah",
            "token": "deadbeef000000000000000000000000",
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


def test_db_dump_reports_per_table_errors_when_table_missing(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Both tables intentionally missing — every query will raise.
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/db/dump")

    assert response.status_code == 200
    body = response.json()
    assert body["tables"]["profiles"] == []
    assert body["tables"]["steps"] == []
    assert body["errors"]["profiles"] is not None  # an exception class name
    assert body["errors"]["steps"] is not None
