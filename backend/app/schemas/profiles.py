"""Pydantic models for /api/profiles."""

from datetime import datetime

from pydantic import BaseModel


class ProfileListEntry(BaseModel):
    """One row in the public users index."""
    username: str
    join_date: datetime
    total_steps_all_time: int


class ProfileListResponse(BaseModel):
    profiles: list[ProfileListEntry]
