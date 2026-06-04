"""HTTP layer for /api/sleep/*.

Thin: parse query params, open a DB connection, dispatch to the
service, return the Pydantic response. All cleaning, aggregation, and
ranking lives in `backend.app.services.sleep` so it stays testable as
plain functions and the route layer never grows business logic.

Mirrors routes/steps.py — same Central Time anchoring for "today",
same default-to-current-ISO-week for the weekly view, same 404
contract on unknown usernames.
"""

import logging
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sleep", tags=["sleep"])


# synzoia anchors all dates to Central Time. The iOS Shortcut writes
# sleep timestamps in UTC; the service translates them. For
# user-facing "today" defaults, we want CT so the no-date-param
# request matches what feels like today.
APP_TIMEZONE = ZoneInfo("America/Chicago")


def _today() -> date:
    """Today's date in the app timezone (Central Time)."""
    return datetime.now(APP_TIMEZONE).date()


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
        return svc.get_global_ranking(conn, as_of or (_today() - timedelta(days=1)))


@router.get(
    "/users/{username}/summary",
    response_model=UserSummaryResponse,
)
def user_summary(username: str) -> UserSummaryResponse:
    username = username.lower()
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_summary(conn, username, _today() - timedelta(days=1))
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
            # Best-effort feed-post for newly-final sessions. Fires for
            # every persisted session — provisional rows skip the post
            # because we wait for the row to settle.
            for s in sessions:
                if s.status == "final":
                    svc.maybe_create_sleep_session_post(
                        conn,
                        session=s,
                    )
            # Apple Health's "Start Date is in the last 1 day" filter
            # is calendar-day-based, so the Shortcut routinely sends
            # samples spanning two nights. The service stores ALL
            # detected sessions (overlap-dedup keeps the DB clean), but
            # the response only returns the latest one — that's what
            # the client UI cares about for the "just woke up, post my
            # night" flow. Earlier sessions remain queryable via GET.
            latest = max(sessions, key=lambda s: s.wake) if sessions else None
            return IngestSleepResponse(
                sessions=(
                    [
                        SleepSessionResponse(
                            id=latest.id or 0,
                            user_id=latest.user_id or user_id,
                            session_type=latest.session_type,
                            status=latest.status,
                            review_flag=latest.review_flag,
                            sleep_date=latest.sleep_date,
                            onset=latest.onset,
                            wake=latest.wake,
                            time_in_bed_min=latest.time_in_bed_min,
                            total_asleep_min=latest.total_asleep_min,
                            awake_min=latest.awake_min,
                            core_min=latest.core_min,
                            deep_min=latest.deep_min,
                            rem_min=latest.rem_min,
                            wakeups=latest.wakeups,
                            # Round to 4 dp so the JSON shows 0.9706
                            # instead of 0.97060000000000002 (float
                            # quantization noise from time_asleep /
                            # time_in_bed).
                            efficiency=round(latest.efficiency, 4),
                            captured_at=latest.captured_at,
                        )
                    ]
                    if latest is not None
                    else []
                )
            )
    except sessions_svc.SleepPayloadError as e:
        raise AppError(422, "invalid_payload", str(e)) from e
    except ValueError as e:
        # Defensive — any other ValueError from the service.
        raise AppError(422, "invalid_sleep", str(e)) from e
    except Exception as e:  # noqa: BLE001 — diagnostic surface
        # An unexpected error in the write path. Log the exception
        # type + a couple of structural counts so we have something
        # actionable in Vercel logs, but do NOT log the raw payload
        # (which contains user health-data timestamps — PII) and do
        # not let the traceback bubble unredacted to the client.
        # Returning an opaque 500 means the response body cannot leak
        # internal state; the exception class + sample counts in the
        # log line are enough to debug from.
        try:
            sample_count = len((req.values or "").split("\n"))
        except Exception:
            sample_count = -1
        logger.exception(
            "sleep ingest failed",
            extra={
                "user_id": user_id,
                "sample_count": sample_count,
                "exception_class": type(e).__name__,
            },
        )
        raise AppError(500, "internal_error", "Internal error") from e


