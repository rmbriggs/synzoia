"""HTTP layer for /api/steps/*.

This module is intentionally thin: parse query params, open a DB
connection, dispatch to the service, return the Pydantic response.
All cleaning, aggregation, and ranking lives in
`backend.app.services.steps` so it stays testable as plain functions
and the route layer never grows business logic.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from backend.app import db
from backend.app.errors import AppError
from backend.app.schemas.steps import (
    GlobalDailyResponse,
    GlobalSummaryResponse,
    GlobalWeeklyResponse,
    UserDailyResponse,
    UserSummaryResponse,
    UserWeeklyResponse,
)
from backend.app.services import steps as svc

router = APIRouter(prefix="/api/steps", tags=["steps"])


def _today() -> date:
    """UTC today. The steps table stores timezone-naive timestamps, so
    UTC is the only consistent bucket we can choose. Revisit when the
    write path lands and we have per-post timezone info."""
    return date.today()


def _iso_monday(d: date) -> date:
    """The Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


# ---------------------------------------------------------------------------
# Global
# ---------------------------------------------------------------------------


@router.get("/daily", response_model=GlobalDailyResponse)
def global_daily(
    date_: Optional[date] = Query(default=None, alias="date"),
) -> GlobalDailyResponse:
    target = date_ or _today()
    with db.get_engine().connect() as conn:
        return svc.get_global_daily(conn, target)


@router.get("/weekly", response_model=GlobalWeeklyResponse)
def global_weekly(
    week_start: Optional[date] = Query(default=None),
) -> GlobalWeeklyResponse:
    start = week_start or _iso_monday(_today())
    with db.get_engine().connect() as conn:
        return svc.get_global_weekly(conn, start)


@router.get("/summary", response_model=GlobalSummaryResponse)
def global_summary() -> GlobalSummaryResponse:
    today = _today()
    week_start = _iso_monday(today)
    with db.get_engine().connect() as conn:
        return svc.get_global_summary(conn, today, week_start)


# ---------------------------------------------------------------------------
# Per-user
# ---------------------------------------------------------------------------


def _user_not_found(username: str) -> AppError:
    return AppError(
        404,
        "user_not_found",
        f"No user named {username!r}.",
    )


@router.get(
    "/users/{username}/daily",
    response_model=UserDailyResponse,
)
def user_daily(
    username: str,
    date_: Optional[date] = Query(default=None, alias="date"),
) -> UserDailyResponse:
    target = date_ or _today()
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_daily(conn, username, target)
    except svc.UserNotFound as e:
        raise _user_not_found(e.username) from e


@router.get(
    "/users/{username}/weekly",
    response_model=UserWeeklyResponse,
)
def user_weekly(
    username: str,
    week_start: Optional[date] = Query(default=None),
) -> UserWeeklyResponse:
    start = week_start or _iso_monday(_today())
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_weekly(conn, username, start)
    except svc.UserNotFound as e:
        raise _user_not_found(e.username) from e


@router.get(
    "/users/{username}/summary",
    response_model=UserSummaryResponse,
)
def user_summary(username: str) -> UserSummaryResponse:
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_summary(conn, username)
    except svc.UserNotFound as e:
        raise _user_not_found(e.username) from e
