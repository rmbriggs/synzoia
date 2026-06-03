"""Shared time-window bounds for the read aggregations.

Steps and sleep both summarize activity over "this week" and "this
month". As of the rolling-windows change these are rolling windows
ending today (inclusive), not ISO weeks or calendar months — so both
services compute their bounds here and stay consistent.
"""
from collections import defaultdict
from datetime import date, timedelta


def rolling_bounds(end: date, days: int) -> tuple[date, date]:
    """Inclusive [start, end] window of `days` days ending at `end`.

    days=7  -> the last 7 days (end-6 .. end)
    days=30 -> the last 30 days (end-29 .. end)
    """
    return (end - timedelta(days=days - 1), end)


def cap_and_sum(rows, cap: int) -> dict[int, int]:
    """Reduce per-(user, day, value) rows to a per-user score: each day's
    value is capped at `cap` (so one monster day can't carry a user), then
    summed. Used for the 30-day capped ranking. `rows` is an iterable of
    (user_id, day, value) tuples."""
    scores: dict[int, int] = defaultdict(int)
    for user_id, _day, value in rows:
        scores[int(user_id)] += min(int(value), cap)
    return dict(scores)
