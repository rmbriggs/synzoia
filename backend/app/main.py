import re
import secrets
from datetime import datetime
from typing import Any

from fastapi import FastAPI, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.app import db
from backend.app.errors import AppError, register_error_handlers
from backend.app.routes import posts as posts_routes
from backend.app.routes import steps as steps_routes

app = FastAPI(title="synzoia")
register_error_handlers(app)
app.include_router(steps_routes.router)
app.include_router(posts_routes.router)

# Live tables after migrations 0003 (pivot) + 0004 (steps) + 0005 (posts).
# Hardcoded — never inject user input here; names are interpolated into
# raw SQL because Postgres won't accept bind params for identifiers.
_TABLES = ("profiles", "steps", "posts")
_DUMP_LIMIT = 100

# Username: 1-30 chars of [A-Za-z0-9_]. Matches the migration's
# char_length(username) between 1 and 30 check and gives a readable
# 422 message instead of letting the DB reject it.
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,30}$")


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


class CreateProfileRequest(BaseModel):
    username: str = Field(min_length=1, max_length=30)


class ProfileResponse(BaseModel):
    username: str
    token: str
    join_date: datetime


@app.post(
    "/api/profiles",
    status_code=status.HTTP_201_CREATED,
    response_model=ProfileResponse,
)
def create_profile(req: CreateProfileRequest) -> ProfileResponse:
    """Sign up: pick a username, get a token. The token is the user's
    iOS-Shortcut credential; the website itself doesn't authenticate."""
    if not _USERNAME_RE.match(req.username):
        raise AppError(
            422,
            "invalid_username",
            "Username must be 1-30 characters of letters, digits, or underscore.",
        )

    # 32 hex chars = 128 bits of entropy; fits the 16-128 char constraint.
    token = secrets.token_hex(16)

    try:
        with db.get_engine().begin() as conn:
            row = (
                conn.execute(
                    text(
                        "INSERT INTO profiles (username, token) "
                        "VALUES (:username, :token) "
                        "RETURNING username, token, join_date"
                    ),
                    {"username": req.username, "token": token},
                )
                .mappings()
                .one()
            )
    except IntegrityError as e:
        # Either username collided (expected) or token collided (1-in-2^128).
        # Both surface as a unique-violation; treat as username-taken since
        # token collisions are not user-actionable and shouldn't happen.
        raise AppError(
            409,
            "username_taken",
            "That username is already taken.",
        ) from e

    return ProfileResponse(**dict(row))
