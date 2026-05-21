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


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = os.environ["DATABASE_URL"]
    return create_engine(url, poolclass=NullPool, future=True)
