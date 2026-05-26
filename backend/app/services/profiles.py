"""Service layer for /api/profiles.

The users-index endpoint joins profiles with their all-time step total.
The `total_steps_all_time` calculation mirrors `get_user_summary` in
services/steps.py — per-CT-day MAX(total), summed across all days —
so the number matches what the Profile page already shows."""

from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.schemas.profiles import (
    ProfileListEntry,
    ProfileListResponse,
)
from backend.app.services.steps import _all_time_daily_max


def list_profiles(conn: Connection) -> ProfileListResponse:
    profile_rows = (
        conn.execute(
            text(
                "SELECT id, username, join_date FROM profiles "
                "ORDER BY username ASC"
            )
        )
        .mappings()
        .all()
    )
    daily_max = _all_time_daily_max(conn)
    totals: dict[int, int] = defaultdict(int)
    for (uid, _d), t in daily_max.items():
        totals[uid] += t
    entries = [
        ProfileListEntry(
            username=p["username"],
            join_date=p["join_date"],
            total_steps_all_time=totals.get(int(p["id"]), 0),
        )
        for p in profile_rows
    ]
    return ProfileListResponse(profiles=entries)
