from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


def _make_sqlite_engine(*table_names: str):
    """Build an in-memory SQLite engine with the named tables.
    StaticPool shares one connection across checkouts so the in-memory
    schema survives between the setup INSERTs and the endpoint's reads.
    `SELECT count(*)` works on any shape, so a single int column suffices."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        for name in table_names:
            conn.execute(text(f"CREATE TABLE {name} (id integer)"))
    return engine


def test_db_check_reports_table_counts_when_all_present(monkeypatch):
    engine = _make_sqlite_engine("profiles", "steps")
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO profiles (id) VALUES (1), (2)"))
        conn.execute(text("INSERT INTO steps (id) VALUES (1)"))
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "stage": "query",
        "tables": {"profiles": 2, "steps": 1},
    }


def test_db_check_marks_missing_tables_as_null(monkeypatch):
    # Only profiles exists; steps is missing.
    engine = _make_sqlite_engine("profiles")
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["stage"] == "query"
    assert body["tables"]["profiles"] == 0
    assert body["tables"]["steps"] is None


def test_db_check_returns_structured_error_when_get_engine_raises(monkeypatch):
    """Before this endpoint was instrumented, a missing DATABASE_URL
    blew up with a bare 500 and the only way to see the exception was
    to dig through serverless logs. Now the response body carries the
    failure class + message so a single curl tells you what's wrong."""

    def _boom():
        raise KeyError("DATABASE_URL")

    monkeypatch.setattr(db, "get_engine", _boom)

    response = TestClient(main.app).get("/api/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "ok": False,
        "stage": "get_engine",
        "error_class": "KeyError",
        "error_message": "'DATABASE_URL'",
    }


def test_db_check_returns_structured_error_when_connect_raises(monkeypatch):
    """Same instrumentation, one layer in: env var resolved fine but
    the connection itself fails (wrong creds, host unreachable, etc.)"""
    from sqlalchemy import create_engine

    # SQLite engine pointed at an unreadable path → connect() raises.
    bad_engine = create_engine("sqlite:////nonexistent/path/db.sqlite")
    monkeypatch.setattr(db, "get_engine", lambda: bad_engine)

    response = TestClient(main.app).get("/api/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["stage"] == "connect"
    assert "error_class" in body
    assert "error_message" in body
