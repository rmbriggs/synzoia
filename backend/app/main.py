from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Load `.env` (or `.env.local`) once at import time so any teammate
# running `uvicorn backend.app.main:app` locally picks up DATABASE_URL,
# SUPABASE_URL, etc., without having to remember to source the file
# manually. python-dotenv is a no-op in production where Vercel
# injects env vars directly, so this is safe to leave on in all
# environments.
load_dotenv()

from backend.app import db
from backend.app.auth import require_user
from backend.app.errors import register_error_handlers
from backend.app.routes import cron as cron_routes
from backend.app.routes import posts as posts_routes
from backend.app.routes import profiles as profiles_routes
from backend.app.routes import sleep as sleep_routes
from backend.app.routes import steps as steps_routes

app = FastAPI(title="synzoia")
register_error_handlers(app)
app.include_router(steps_routes.router)
app.include_router(posts_routes.router)
app.include_router(cron_routes.router)
app.include_router(profiles_routes.router)
app.include_router(sleep_routes.router)

# Live tables after migrations 0003 (pivot) + 0004 (steps) + 0005 (posts)
# + 0008 (sleep). Hardcoded — never inject user input here; names are
# interpolated into raw SQL because Postgres won't accept bind params
# for identifiers.
_TABLES = ("profiles", "steps", "posts", "sleep")
_DUMP_LIMIT = 100

# Columns redacted from the /api/db/dump response per-table. The
# `profiles.token` value IS the auth credential, so dumping it would
# let any logged-in user impersonate anyone else. Drop it from the
# response shape entirely (the column still exists in the DB).
_REDACTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "profiles": ("token",),
}


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/health/db")
def health_db() -> dict:
    """Connectivity probe: counts rows in each v1 table. Returns 200
    even when the DB is unreachable — the response body's `ok` field
    + `stage`/`error_*` fields tell you what went wrong without
    needing to dig through serverless logs. Previously this raised a
    bare 500 when the env var was missing or the connection failed,
    which is opaque from a browser/curl.

    Stages, in order:
      1. get_engine — env var lookup + engine factory
      2. connect    — opening a Postgres connection
      3. query      — running SELECT count(*) per table (per-table
                       failures recorded in tables[name] = null)"""
    try:
        engine = db.get_engine()
    except Exception as e:  # noqa: BLE001 — diagnostic surface, by design
        return {
            "ok": False,
            "stage": "get_engine",
            "error_class": type(e).__name__,
            "error_message": str(e),
        }

    try:
        with engine.connect() as conn:
            tables: dict[str, int | None] = {}
            for name in _TABLES:
                try:
                    count = conn.execute(
                        text(f"SELECT count(*) FROM {name}")
                    ).scalar()
                    tables[name] = int(count or 0)
                except SQLAlchemyError:
                    tables[name] = None
    except Exception as e:  # noqa: BLE001 — diagnostic surface, by design
        return {
            "ok": False,
            "stage": "connect",
            "error_class": type(e).__name__,
            "error_message": str(e),
        }

    return {
        "ok": all(v is not None for v in tables.values()),
        "stage": "query",
        "tables": tables,
    }


@app.get("/api/db/dump")
def db_dump(user_id: int = Depends(require_user)) -> dict:
    """Dev/admin: dump up to _DUMP_LIMIT rows from each v1 table. Backs
    the /db page used for demos and debugging.

    Hardened against credential leakage:
      - Requires a valid Bearer token (anonymous requests get 401).
      - Strips `_REDACTED_COLUMNS` per table from the response — most
        importantly `profiles.token`, which IS the auth credential and
        would otherwise let any logged-in user impersonate everyone
        else.

    Per-table query failures are reported in `errors[name]`; the table's
    row list is left empty rather than erroring the whole response."""
    del user_id  # auth-only; identity not used inside the handler
    engine = db.get_engine()
    tables: dict[str, list[dict[str, Any]]] = {}
    errors: dict[str, str | None] = {}
    with engine.connect() as conn:
        for name in _TABLES:
            redacted = _REDACTED_COLUMNS.get(name, ())
            try:
                rows = (
                    conn.execute(text(f"SELECT * FROM {name} LIMIT {_DUMP_LIMIT}"))
                    .mappings()
                    .all()
                )
                tables[name] = [
                    {k: v for k, v in dict(r).items() if k not in redacted}
                    for r in rows
                ]
                errors[name] = None
            except SQLAlchemyError as e:
                tables[name] = []
                errors[name] = type(e).__name__
    return {
        "tables": jsonable_encoder(tables),
        "errors": errors,
        "limit": _DUMP_LIMIT,
    }


