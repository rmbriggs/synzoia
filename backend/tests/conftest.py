import os

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:6543/test",
)


@pytest.fixture(autouse=True)
def _reset_engine_cache():
    """Clear the lru_cache on `db.get_engine` around every test so no test
    inherits a stale engine bound to a previous test's DATABASE_URL."""
    from backend.app import db

    db.get_engine.cache_clear()
    yield
    db.get_engine.cache_clear()
