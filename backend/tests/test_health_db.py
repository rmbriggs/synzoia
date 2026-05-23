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
    engine = _make_sqlite_engine("profiles")
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO profiles (id) VALUES (1), (2)"))
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "tables": {"profiles": 2}}


def test_db_check_marks_missing_tables_as_null(monkeypatch):
    # Migration hasn't run; profiles is missing.
    engine = _make_sqlite_engine()  # no tables
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/health/db")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["tables"]["profiles"] is None
