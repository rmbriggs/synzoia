from sqlalchemy.pool import NullPool

from backend.app import db


def test_engine_uses_null_pool():
    """Serverless functions must not pool DB connections themselves;
    that job belongs to Supabase's pgbouncer pooler."""
    engine = db.get_engine()
    assert isinstance(engine.pool, NullPool)
