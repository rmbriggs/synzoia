"""HTTP layer for /api/steps/*.

This module is intentionally thin: parse query params, open a DB
connection, dispatch to the service, return the Pydantic response.
All cleaning, aggregation, and ranking lives in
`backend.app.services.steps` so it stays testable as plain functions
and the route layer never grows business logic.
"""

from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, status

from backend.app import db
from backend.app.auth import require_user
from backend.app.errors import AppError
from backend.app.schemas.steps import (
    CreateStepRequest,
    CreateStepResponse,
    GlobalDailyResponse,
    GlobalSummaryResponse,
    GlobalWeeklyResponse,
    UserDailyResponse,
    UserMonthlyResponse,
    UserSummaryResponse,
    UserWeeklyResponse,
)
from backend.app.services import steps as svc

router = APIRouter(prefix="/api/steps", tags=["steps"])


# ryzome anchors all dates to Central Time. The iOS Shortcut writes
# step timestamps in local (CT) time, so bucketing the default "today"
# the same way keeps no-date-param queries consistent with what got
# posted. The frontend also passes ?date= as a CT date.
APP_TIMEZONE = ZoneInfo("America/Chicago")


def _today() -> date:
    """Today's date in the app timezone (Central Time)."""
    return datetime.now(APP_TIMEZONE).date()


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
    as_of: Optional[date] = Query(default=None),
) -> GlobalWeeklyResponse:
    anchor = as_of or _today()
    with db.get_engine().connect() as conn:
        return svc.get_global_weekly(conn, anchor)


@router.get("/summary", response_model=GlobalSummaryResponse)
def global_summary() -> GlobalSummaryResponse:
    with db.get_engine().connect() as conn:
        return svc.get_global_summary(conn, _today())


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
    username = username.lower()
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
    as_of: Optional[date] = Query(default=None),
) -> UserWeeklyResponse:
    username = username.lower()
    anchor = as_of or _today()
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_weekly(conn, username, anchor)
    except svc.UserNotFound as e:
        raise _user_not_found(e.username) from e


@router.get(
    "/users/{username}/monthly",
    response_model=UserMonthlyResponse,
)
def user_monthly(
    username: str,
    as_of: Optional[date] = Query(default=None),
) -> UserMonthlyResponse:
    """One user's stats for the rolling last 30 days ending `as_of` (CT today by default)."""
    username = username.lower()
    anchor = as_of or _today()
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_monthly(conn, username, anchor)
    except svc.UserNotFound as e:
        raise _user_not_found(e.username) from e


@router.get("/ranking", response_model=GlobalWeeklyResponse)
def global_ranking(
    as_of: Optional[date] = Query(default=None),
) -> GlobalWeeklyResponse:
    with db.get_engine().connect() as conn:
        return svc.get_global_ranking(conn, as_of or _today())


@router.get(
    "/users/{username}/summary",
    response_model=UserSummaryResponse,
)
def user_summary(username: str) -> UserSummaryResponse:
    username = username.lower()
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_summary(conn, username, _today())
    except svc.UserNotFound as e:
        raise _user_not_found(e.username) from e


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateStepResponse,
)
def create_step(
    req: CreateStepRequest,
    user_id: int = Depends(require_user),
) -> CreateStepResponse:
    """POST /api/steps — write a step snapshot on behalf of the
    Bearer-token user. Called by the iOS Shortcut every time Apple
    Health step data is synced. `user_id` is resolved from the token,
    NEVER from the request body (per CLAUDE.md). Also fires
    milestone-detection in the same transaction."""
    with db.get_engine().begin() as conn:
        response = svc.create_step(
            conn,
            user_id=user_id,
            timestamp=req.timestamp,
            total=req.total,
        )
        svc.detect_and_insert_milestone(
            conn,
            user_id=user_id,
            timestamp=req.timestamp,
        )
        return response
