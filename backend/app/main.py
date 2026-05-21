from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.app import db

app = FastAPI(title="synzoia")

# Tables introduced by 0001_initial.sql. Hardcoded list — never inject
# user input here; the names are interpolated into raw SQL because
# Postgres won't accept bind params for identifiers.
_TABLES = ("profiles", "groups", "memberships", "sleep_posts", "streaks")


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/health/db")
def health_db() -> dict:
    """Connectivity probe: counts rows in each v1 table. Returns
    `tables[name] = null` for any table whose query fails (e.g. the
    migration hasn't run yet) so the frontend can distinguish "DB down"
    from "migration pending"."""
    engine = db.get_engine()
    tables: dict[str, int | None] = {}
    with engine.connect() as conn:
        for name in _TABLES:
            try:
                count = conn.execute(text(f"SELECT count(*) FROM {name}")).scalar()
                tables[name] = int(count or 0)
            except SQLAlchemyError:
                tables[name] = None
    return {"ok": all(v is not None for v in tables.values()), "tables": tables}
