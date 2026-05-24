from sqlalchemy.pool import NullPool

from backend.app import db
from backend.app.db import _normalize_scheme


def test_engine_uses_null_pool():
    """Serverless functions must not pool DB connections themselves;
    that job belongs to Supabase's pgbouncer pooler."""
    engine = db.get_engine()
    assert isinstance(engine.pool, NullPool)


def test_normalize_scheme_rewrites_postgresql_to_psycopg_v3():
    """SQLAlchemy defaults `postgresql://` to psycopg2, which we don't
    ship. Normalize to `postgresql+psycopg://` (psycopg v3) so the
    factory works with whatever URL shape Supabase's UI hands the user."""
    out = _normalize_scheme(
        "postgresql://postgres.abcd:pw@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
    )
    assert out.startswith("postgresql+psycopg://")
    assert "postgres.abcd:pw@aws-0-us-east-2.pooler.supabase.com:6543/postgres" in out


def test_normalize_scheme_rewrites_short_postgres_scheme():
    """Some Supabase UI panels still hand out the older `postgres://`
    prefix. Same fix — rewrite to `postgresql+psycopg://`."""
    out = _normalize_scheme("postgres://u:p@host:6543/db")
    assert out == "postgresql+psycopg://u:p@host:6543/db"


def test_normalize_scheme_leaves_explicit_driver_alone():
    """A URL that already names a driver (psycopg, asyncpg, ...) is a
    deliberate choice; don't rewrite it."""
    for url in (
        "postgresql+psycopg://u:p@h:6543/db",
        "postgresql+asyncpg://u:p@h:5432/db",
        "sqlite:///:memory:",
    ):
        assert _normalize_scheme(url) == url
