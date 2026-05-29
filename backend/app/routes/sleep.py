"""HTTP layer for /api/sleep/*.

Thin: parse query params, open a DB connection, dispatch to the
service, return the Pydantic response. All cleaning, aggregation, and
ranking lives in `backend.app.services.sleep` so it stays testable as
plain functions and the route layer never grows business logic.

Mirrors routes/steps.py — same Central Time anchoring for "today",
same default-to-current-ISO-week for the weekly view, same 404
contract on unknown usernames.
"""

from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.exc import IntegrityError

from backend.app import db
from backend.app.auth import require_user
from backend.app.errors import AppError
from backend.app.schemas.sleep import (
    CreateSleepRequest,
    CreateSleepResponse,
    GlobalDailyResponse,
    GlobalSummaryResponse,
    GlobalWeeklyResponse,
    UserDailyResponse,
    UserMonthlyResponse,
    UserSummaryResponse,
    UserWeeklyResponse,
)
from backend.app.services import sleep as svc

router = APIRouter(prefix="/api/sleep", tags=["sleep"])


# synzoia anchors all dates to Central Time. The iOS Shortcut writes
# sleep timestamps in UTC; the service translates them. For
# user-facing "today" defaults, we want CT so the no-date-param
# request matches what feels like today.
APP_TIMEZONE = ZoneInfo("America/Chicago")


def _today() -> date:
    """Today's date in the app timezone (Central Time)."""
    return datetime.now(APP_TIMEZONE).date()


def _iso_monday(d: date) -> date:
    """The Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def _user_not_found(username: str) -> AppError:
    return AppError(
        404,
        "user_not_found",
        f"No user named {username!r}.",
    )


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
    "/users/{username}/monthly",
    response_model=UserMonthlyResponse,
)
def user_monthly(
    username: str,
    month: Optional[str] = Query(default=None, regex=r"^\d{4}-\d{2}$"),
) -> UserMonthlyResponse:
    """One user's stats for a CT calendar month. `month` is YYYY-MM
    in CT; defaults to the current CT month."""
    if month:
        year, mo = month.split("-")
        target = date(int(year), int(mo), 1)
    else:
        today = _today()
        target = today.replace(day=1)
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_monthly(conn, username, target)
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


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateSleepResponse,
)
def create_sleep(
    req: CreateSleepRequest,
    user_id: int = Depends(require_user),
) -> CreateSleepResponse:
    """POST /api/sleep — write one night's sleep row on behalf of the
    Bearer-token user. Called by the iOS Shortcut every morning when
    Apple Health sleep data is synced. `user_id` is resolved from the
    token; `night_of` is computed by the service from wake_time's CT
    date (NEVER trusted from the body, per CLAUDE.md)."""
    try:
        with db.get_engine().begin() as conn:
            return svc.create_sleep(
                conn,
                user_id=user_id,
                bedtime=req.bedtime,
                wake_time=req.wake_time,
                duration_min=req.duration_min,
                rem_minutes=req.rem_minutes,
                core_minutes=req.core_minutes,
                deep_minutes=req.deep_minutes,
                awake_minutes=req.awake_minutes,
            )
    except ValueError as e:
        # wake_time <= bedtime, caught in the service before SQL fires.
        raise AppError(422, "invalid_sleep", str(e)) from e
    except IntegrityError as e:
        # UNIQUE (user_id, night_of) — Shortcut tried to double-post.
        raise AppError(
            409,
            "sleep_already_posted",
            "A sleep row already exists for this night. "
            "Delete it first if you want to overwrite.",
        ) from e
