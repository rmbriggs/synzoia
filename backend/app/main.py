from typing import Any

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.app import db

app = FastAPI(title="synzoia")

# Tables introduced by 0001_initial.sql. Hardcoded list — never inject
# user input here; the names are interpolated into raw SQL because
# Postgres won't accept bind params for identifiers.
_TABLES = ("profiles", "groups", "memberships", "sleep_posts", "streaks")
_DUMP_LIMIT = 100


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


@app.get("/api/db/dump")
def db_dump() -> dict:
    """Dev-only: dump up to _DUMP_LIMIT rows from each v1 table. Backs the
    /db page. Per-table query failures are reported in `errors[name]` and
    the table's row list is left empty rather than erroring the whole
    response."""
    engine = db.get_engine()
    tables: dict[str, list[dict[str, Any]]] = {}
    errors: dict[str, str | None] = {}
    with engine.connect() as conn:
        for name in _TABLES:
            try:
                rows = (
                    conn.execute(text(f"SELECT * FROM {name} LIMIT {_DUMP_LIMIT}"))
                    .mappings()
                    .all()
                )
                tables[name] = [dict(r) for r in rows]
                errors[name] = None
            except SQLAlchemyError as e:
                tables[name] = []
                errors[name] = type(e).__name__
    return {
        "tables": jsonable_encoder(tables),
        "errors": errors,
        "limit": _DUMP_LIMIT,
    }
