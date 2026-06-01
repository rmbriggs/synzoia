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

from backend.app import db
from backend.app.auth import require_user
from backend.app.errors import AppError
from backend.app.schemas.sleep import (
    GlobalDailyResponse,
    GlobalSummaryResponse,
    GlobalWeeklyResponse,
    IngestSleepRequest,
    IngestSleepResponse,
    SleepSessionResponse,
    UserDailyResponse,
    UserMonthlyResponse,
    UserSummaryResponse,
    UserWeeklyResponse,
)
from backend.app.services import sleep as svc
from backend.app.services import sleep_sessions as sessions_svc

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
    response_model=IngestSleepResponse,
)
def ingest_sleep(
    req: IngestSleepRequest,
    user_id: int = Depends(require_user),
) -> IngestSleepResponse:
    """POST /api/sleep — ingest a raw HealthKit sample window.

    Angela's iOS Shortcut polls every ~30 min and sends the full
    night-plus-naps window. We:
      1. Parse the newline-joined sample arrays.
      2. Sessionize on >60-min gaps (separates night from naps and
         splits a night interrupted by a long awakening).
      3. Classify each session as 'night' (onset 20:00-05:00 in the
         payload's offset) or 'nap'.
      4. Compute per-session metrics (asleep, awake, per-stage,
         wakeups, efficiency).
      5. Upsert with overlap-dedup so repeated polls of the same
         in-progress session update the same row instead of creating
         duplicates.

    Returns an array of persisted sessions (one entry per detected
    session). `user_id` is resolved from the Bearer token.

    Per CLAUDE.md: user_id is NEVER trusted from the body; all date /
    time / classification fields are server-derived from the samples.
    """
    try:
        with db.get_engine().begin() as conn:
            sessions = sessions_svc.ingest_payload(
                conn,
                user_id=user_id,
                values=req.values,
                starts=req.starts,
                ends=req.ends,
                types=req.types,
                duration=req.duration,
                timestamp=req.timestamp,
            )
            # Best-effort feed-post for newly-final sessions. Provisional
            # rows don't fire a post — we wait for the row to settle.
            # (Implemented by the service layer; here we just emit the
            # response.)
            for s in sessions:
                if s.status == "final":
                    svc.maybe_create_sleep_session_post(
                        conn,
                        session=s,
                    )
            return IngestSleepResponse(
                sessions=[
                    SleepSessionResponse(
                        id=s.id or 0,
                        user_id=s.user_id or user_id,
                        session_type=s.session_type,
                        status=s.status,
                        review_flag=s.review_flag,
                        sleep_date=s.sleep_date,
                        onset=s.onset,
                        wake=s.wake,
                        time_in_bed_min=s.time_in_bed_min,
                        total_asleep_min=s.total_asleep_min,
                        awake_min=s.awake_min,
                        core_min=s.core_min,
                        deep_min=s.deep_min,
                        rem_min=s.rem_min,
                        wakeups=s.wakeups,
                        efficiency=s.efficiency,
                        captured_at=s.captured_at,
                    )
                    for s in sessions
                ]
            )
    except sessions_svc.SleepPayloadError as e:
        raise AppError(422, "invalid_payload", str(e)) from e
    except ValueError as e:
        # Defensive — any other ValueError from the service.
        raise AppError(422, "invalid_sleep", str(e)) from e
    except Exception as e:
        # Re-raise so FastAPI logs the traceback in Vercel logs.
        # Intentionally not swallowed; this is a write path.
        # noqa: BLE001 — diagnostic surface
        raise


