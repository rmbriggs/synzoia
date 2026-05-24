"""HTTP layer for /api/cron/*.

Endpoints are GET-only because Vercel Cron Jobs send GET requests.
Each one verifies a Bearer-CRON_SECRET header (set in Vercel env)
before dispatching to its service.

Cron schedule lives in `vercel.json`. The daily-recap cron fires at
`0 11 * * *` UTC = 6am CDT (Mar–Nov) / 5am CST (Nov–Mar). The DST
drift is an accepted trade-off for the class-project demo; the cron
could be made TZ-aware later by firing at both 11 and 12 UTC with a
guard if needed."""

from __future__ import annotations

import os
import secrets as _secrets
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header

from backend.app import db
from backend.app.errors import AppError
from backend.app.services import cron as svc

router = APIRouter(prefix="/api/cron", tags=["cron"])

APP_TZ = ZoneInfo("America/Chicago")


def _today_ct() -> date:
    """Today's date in app timezone. Pulled out as a module-level
    function so tests can monkeypatch it deterministically."""
    return datetime.now(APP_TZ).date()


def _verify_cron_secret(authorization: Optional[str]) -> None:
    """Reject anything that isn't `Bearer <CRON_SECRET>` (with the
    CRON_SECRET env var matching exactly, constant-time compare)."""
    expected = os.environ.get("CRON_SECRET")
    if not expected:
        raise AppError(
            503,
            "cron_misconfigured",
            "CRON_SECRET is not set on the backend.",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(
            401,
            "unauthenticated",
            "Missing or invalid Authorization header.",
        )
    presented = authorization[len("Bearer ") :].strip()
    if not _secrets.compare_digest(presented, expected):
        raise AppError(401, "unauthenticated", "Invalid cron secret.")


@router.get("/daily-recap")
def daily_recap(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Vercel cron entry. Writes a leaderboard_recap post for yesterday
    CT (idempotent) or returns a structured skip reason."""
    _verify_cron_secret(authorization)
    with db.get_engine().begin() as conn:
        return svc.write_daily_recap(conn, today=_today_ct())
