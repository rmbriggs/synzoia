"""Single source of truth for the SQLite test schema.

These DDL strings are hand-mirrored from the real Postgres schema in
``backend/migrations/*.sql``. One definition per table — test files
must NOT hand-write ``CREATE TABLE``; call :func:`make_engine` instead.

Why this module exists: before it, every test file copy-pasted its own
``CREATE TABLE`` block and they drifted. At the time of writing, three
files carried three different ``sleep`` shapes — one still had the
``UNIQUE (user_id, night_of)`` constraint that migration 0009 dropped,
and another omitted columns that are NOT NULL in production. When a
migration changes a table, update the mirror HERE and every test picks
it up.

Postgres → SQLite mapping used in the mirrors:
  - BIGSERIAL / GENERATED      → integer primary key autoincrement
  - timestamptz / date         → text (ISO strings compare correctly)
  - boolean                    → integer (0/1)
  - now()                      → (datetime('now'))
CHECK / NOT NULL / UNIQUE constraints are kept — SQLite enforces them,
which is as close to "the DB is the last line of defense" as the
in-memory harness gets. (RLS is Postgres-only and NOT exercised here.)
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

# Mirrors migrations 0003 (pivot) + 0012 (lowercase usernames).
_PROFILES = (
    "CREATE TABLE profiles ("
    "id integer primary key autoincrement, "
    "username text not null unique, "
    "token text not null unique, "
    "join_date text not null default (datetime('now')))"
)

# Mirrors migration 0004.
_STEPS = (
    "CREATE TABLE steps ("
    "id integer primary key autoincrement, "
    "user_id integer not null, "
    "timestamp text not null, "
    "total integer not null)"
)

# Mirrors migrations 0005 + 0007 (details/body columns).
_POSTS = (
    "CREATE TABLE posts ("
    "id integer primary key autoincrement, "
    "user_id integer not null, "
    "username text not null, "
    "type text not null, "
    "timestamp text not null, "
    "details text, "
    "body text)"
)

# Mirrors migrations 0008 + 0009: full session shape, NO unique
# (user_id, night_of) — 0009 dropped it; multiple sessions per user
# per date is the supported shape.
_SLEEP = (
    "CREATE TABLE sleep ("
    "id integer primary key autoincrement, "
    "user_id integer not null, "
    "bedtime text not null, "
    "wake_time text not null, "
    "duration_min integer not null, "
    "rem_minutes integer, "
    "core_minutes integer, "
    "deep_minutes integer, "
    "awake_minutes integer, "
    "night_of text not null, "
    "session_type text not null default 'night' "
    "  check (session_type in ('night', 'nap')), "
    "status text not null default 'final' "
    "  check (status in ('provisional', 'final')), "
    "review_flag integer not null default 0, "
    "captured_at text not null default (datetime('now')), "
    "onset_at text not null, "
    "sleep_date text not null, "
    "created_at text not null default (datetime('now')))"
)

SCHEMA: dict[str, str] = {
    "profiles": _PROFILES,
    "steps": _STEPS,
    "posts": _POSTS,
    "sleep": _SLEEP,
}


def make_engine(*tables: str) -> Engine:
    """In-memory SQLite engine with the named tables created.

    No arguments → all tables. StaticPool + check_same_thread=False so
    FastAPI's TestClient (which runs handlers on worker threads) shares
    the single in-memory database with the test body.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    names = tables or tuple(SCHEMA)
    with engine.begin() as conn:
        for name in names:
            conn.execute(text(SCHEMA[name]))
    return engine
