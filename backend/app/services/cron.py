"""Daily leaderboard recap.

Run by Vercel cron once a day (see backend/app/routes/cron.py +
vercel.json). Computes yesterday's top 3 step posters in Central
Time and inserts a single `leaderboard_recap` post into the feed.

Idempotent: if a recap for that date already exists, the call is a
no-op. Bail-cleanly: if no one posted yesterday, no post is created."""

from __future__ import annotations

import json as _json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.services import steps as svc_steps


def write_daily_recap(conn: Connection, today: date) -> dict:
    """Insert one `leaderboard_recap` post for (today - 1 day), if one
    doesn't exist yet and there's data to recap. `today` should be the
    CT date — the caller is responsible for that.

    Returns one of:
      {"inserted": {<post row>}}
      {"skipped": "already_posted"}
      {"skipped": "no_data"}
    """
    yesterday = today - timedelta(days=1)
    yesterday_iso = yesterday.isoformat()

    existing_rows = (
        conn.execute(
            text("SELECT details FROM posts WHERE type = 'leaderboard_recap'"),
        )
        .mappings()
        .all()
    )
    for r in existing_rows:
        raw = r["details"]
        if raw is None:
            continue
        d = _json.loads(raw) if isinstance(raw, str) else raw
        if d.get("date") == yesterday_iso:
            return {"skipped": "already_posted"}

    daily_totals = svc_steps._daily_totals_in_range(conn, yesterday, yesterday)
    if not daily_totals:
        return {"skipped": "no_data"}

    usernames = svc_steps._usernames_for(
        conn, {uid for uid, _, _ in daily_totals}
    )
    ranked = sorted(
        ((uid, total) for uid, _, total in daily_totals if uid in usernames),
        key=lambda x: (-x[1], usernames[x[0]]),
    )[:3]
    if not ranked:
        return {"skipped": "no_data"}

    top = [
        {"username": usernames[uid], "total": int(total)}
        for uid, total in ranked
    ]
    top1_uid, _top1_total = ranked[0]
    top1_username = usernames[top1_uid]

    details_str = _json.dumps({"date": yesterday_iso, "top": top})
    body = "Yesterday's top 3"
    now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    row = (
        conn.execute(
            text(
                "INSERT INTO posts "
                "(user_id, username, type, timestamp, details, body) "
                "VALUES (:uid, :u, 'leaderboard_recap', :ts, :details, :body) "
                "RETURNING id, user_id, username, type, timestamp, details, body"
            ),
            {
                "uid": top1_uid,
                "u": top1_username,
                "ts": now_utc_naive,
                "details": details_str,
                "body": body,
            },
        )
        .mappings()
        .one()
    )
    return {"inserted": dict(row)}
