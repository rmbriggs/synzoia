"""Database engine factory.

Serverless functions cannot maintain their own connection pool — each
invocation is a fresh process. Pooling lives in Supabase's pgbouncer
(connect via the *pooler* URL on port 6543, transaction mode). The
SQLAlchemy engine here uses NullPool so it opens-and-closes per checkout.
"""

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool


def _normalize_scheme(url: str) -> str:
    """Rewrite the URL scheme so SQLAlchemy uses our installed driver.

    Supabase's connection-string UI hands you `postgres://...` or
    `postgresql://...`. SQLAlchemy maps both of those to `psycopg2`,
    which we don't ship — we ship `psycopg` (v3) via
    `psycopg[binary]==3.2.13`. The right SQLAlchemy URL prefix for
    that driver is `postgresql+psycopg://`.

    Anything that already specifies a driver (e.g. `postgresql+psycopg`,
    `postgresql+asyncpg`) is passed through unchanged."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = _normalize_scheme(os.environ["DATABASE_URL"])
    return create_engine(url, poolclass=NullPool, future=True)
