# Users index + per-user page restructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/users` index page listing every user, and restructure `/u/:username` into a two-tab layout (Summary | Feed) that adds a monthly summary card and a per-user feed showing posts that mention the user.

**Architecture:** Single PR on branch `worktree-users-pages`, three commits in TDD order. (1) Backend: new `GET /api/steps/users/:u/monthly`, new `GET /api/profiles` list, and extended `GET /api/posts/users/:u` that includes `leaderboard_recap` posts mentioning the user. (2) Frontend Users index page + route + nav links (top + bottom), with two shared-UI extractions (`ErrorCard`, `RowListSkeleton`). (3) Frontend Profile page restructure with `TabStrip`, new `ThisMonthCard`, new `FeedPanel`, and shared post-renderer extraction.

**Tech Stack:** FastAPI + SQLAlchemy + psycopg v3 (backend), React + Vite + React Query + Tailwind (frontend), pytest (in-memory SQLite for unit tests), vitest + React Testing Library (frontend), Supabase Postgres, Vercel hosting.

**Spec:** `docs/superpowers/specs/2026-05-25-users-pages-design.md`

**Branch:** `worktree-users-pages` (already created, branched from origin/main). Spec commit `f47cb48` is already on this branch as commit 1; the plan adds **three more commits** (one per phase below).

---

## File Structure

### Commit 2 — Backend (`fix/feat: backend endpoints for users-pages`)

| File | Action | Responsibility |
|---|---|---|
| `backend/app/schemas/steps.py` | modify | Add `UserMonthlyResponse` Pydantic model |
| `backend/app/schemas/profiles.py` | create | `ProfileListEntry`, `ProfileListResponse` |
| `backend/app/services/steps.py` | modify | Add `get_user_monthly(conn, username, month_start)` |
| `backend/app/services/profiles.py` | create | `list_profiles(conn) -> ProfileListResponse` |
| `backend/app/services/posts.py` | modify | Extend `list_user_feed` to include recap mentions |
| `backend/app/routes/steps.py` | modify | Add `GET /users/{u}/monthly` route |
| `backend/app/routes/profiles.py` | create | Router with both `POST /api/profiles` (moved from main) and `GET /api/profiles` |
| `backend/app/main.py` | modify | Remove inline POST handler; include new `profiles_routes.router` |
| `backend/tests/test_steps_monthly.py` | create | Service + route tests for the monthly endpoint |
| `backend/tests/test_profiles_list.py` | create | Tests for `GET /api/profiles` |
| `backend/tests/test_posts_routes.py` | modify | Add 2 cases for recap-mention behavior |
| `backend/tests/test_profiles.py` | modify | Adjust import path if needed (POST now lives in a router) |

### Commit 3 — Frontend Users index (`feat(frontend): /users index page + nav`)

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/components/ui/ErrorCard.tsx` | create | Shared error card with retry button (extracted) |
| `frontend/src/components/ui/RowListSkeleton.tsx` | create | Shared 6-row skeleton (extracted/renamed from `LeaderboardSkeleton`) |
| `frontend/src/pages/Leaderboard.tsx` | modify | Import shared `ErrorCard` + `RowListSkeleton`; drop local copies |
| `frontend/src/api/profiles.ts` | modify | Add `getProfiles()` + `ProfileListEntry`/`ProfileListResponse` types |
| `frontend/src/pages/Users.tsx` | create | New `/users` page |
| `frontend/src/App.tsx` | modify | Add `<Route path="/users" element={<Users />} />` |
| `frontend/src/components/layout/AppLayout.tsx` | modify | Insert "Users" entries in top nav + bottom pill |
| `frontend/src/__tests__/smoke.test.tsx` | modify | Add `/users` to the route list |
| `frontend/src/__tests__/Users.test.tsx` | create | Component tests |

### Commit 4 — Frontend Profile tabs + monthly card (`feat(frontend): /u/:username tabs + monthly card`)

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/components/feed/MilestonePost.tsx` | create | Extracted from Feed.tsx |
| `frontend/src/components/feed/RecapPost.tsx` | create | Extracted from Feed.tsx |
| `frontend/src/components/feed/GenericPost.tsx` | create | Extracted from Feed.tsx |
| `frontend/src/components/feed/FeedSkeleton.tsx` | create | Extracted from Feed.tsx (used by both Feed and FeedPanel) |
| `frontend/src/components/ui/DailyBars.tsx` | create | Extracted/renamed from Profile.tsx's local `WeeklyBars` |
| `frontend/src/pages/Feed.tsx` | modify | Import the four renderers from `components/feed/` |
| `frontend/src/api/steps.ts` | modify | Add `UserMonthlyResponse` type + `getUserMonthly()` |
| `frontend/src/pages/Profile.tsx` | rewrite | TabStrip with Summary + Feed; new ThisMonthCard; new FeedPanel |
| `frontend/src/__tests__/Profile.test.tsx` | rewrite | Tab tests + monthly card test + feed-panel test |
| `frontend/src/__tests__/Feed.test.tsx` | modify | Adjust import paths only |

---

## How to run tests

**Backend (from worktree root):**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/ -v
```

The worktree does not have its own venv; we reuse the main checkout's venv. Tests use in-memory SQLite via `_engine_with_users()` helpers in each test module — no real DB needed.

**Frontend (from worktree root):**

```bash
cd frontend && npm test -- --run
```

`--run` makes vitest exit instead of going into watch mode.

---

# Commit 2 — Backend

> Run `pytest backend/tests/ -v` between tasks to keep the suite green. Do NOT commit until the entire phase passes.

## Task 2.1 — Schema: `UserMonthlyResponse`

**Files:**
- Modify: `backend/app/schemas/steps.py`

- [ ] **Step 1: Inspect the existing weekly schema to match its shape**

```bash
grep -nA 8 "class UserWeeklyResponse" backend/app/schemas/steps.py
```

Expected: a Pydantic model with `username: str`, `week_start: date`, `week_end: date`, `weekly_total: int`, `rank_this_week: int | None`, `daily_breakdown: list[DailyTotal]`.

- [ ] **Step 2: Add `UserMonthlyResponse` directly below `UserWeeklyResponse`**

Edit `backend/app/schemas/steps.py`, insert this class right after `UserWeeklyResponse`:

```python
class UserMonthlyResponse(BaseModel):
    """One user's stats for a single CT calendar month."""
    username: str
    month_start: date
    month_end: date
    monthly_total: int
    rank_this_month: int | None
    daily_breakdown: list[DailyTotal]
```

- [ ] **Step 3: Sanity-check imports compile**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/python -c "from backend.app.schemas.steps import UserMonthlyResponse; print('ok')"
```

Expected: `ok`.

## Task 2.2 — Service: `get_user_monthly`

**Files:**
- Modify: `backend/app/services/steps.py`
- Test: `backend/tests/test_steps_monthly.py` (create)

- [ ] **Step 1: Write the failing test file**

Create `backend/tests/test_steps_monthly.py`:

```python
"""Tests for get_user_monthly service.

Uses in-memory SQLite via the same _engine_with_users helper pattern as
the rest of the steps test suite. Timestamps in fixtures are stored as
naive UTC (matching what psycopg sees from the Shortcut)."""

from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app.services import steps as svc


def _engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE profiles ("
                "id integer primary key autoincrement, "
                "username text not null unique, "
                "token text not null unique, "
                "join_date text not null default (datetime('now')))"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE steps ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "timestamp text not null, "
                "total integer not null)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO profiles (id, username, token) VALUES "
                "(1, 'alice', 'alice_token_aaaaaaaaaaaaaaaaa'), "
                "(2, 'bob', 'bob_token_bbbbbbbbbbbbbbbbbbb')"
            )
        )
    return engine


def test_get_user_monthly_returns_expected_shape():
    """May 2026 — Alice has one day with 9000 steps on the 23rd CT."""
    engine = _engine()
    with engine.begin() as conn:
        # UTC 2026-05-24T02:00 → CT 2026-05-23T21:00 → CT date 2026-05-23
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) "
                "VALUES (1, '2026-05-24T02:00:00', 9000)"
            )
        )

    with engine.connect() as conn:
        result = svc.get_user_monthly(conn, "alice", date(2026, 5, 1))

    assert result.username == "alice"
    assert result.month_start == date(2026, 5, 1)
    assert result.month_end == date(2026, 5, 31)
    assert result.monthly_total == 9000
    # daily_breakdown contains only the day(s) the user actually walked.
    assert len(result.daily_breakdown) == 1
    assert result.daily_breakdown[0].date == date(2026, 5, 23)
    assert result.daily_breakdown[0].total == 9000


def test_get_user_monthly_returns_empty_breakdown_for_inactive_month():
    """A month the user had zero step writes returns empty list, not zeros."""
    engine = _engine()
    with engine.connect() as conn:
        result = svc.get_user_monthly(conn, "alice", date(2026, 4, 1))

    assert result.monthly_total == 0
    assert result.daily_breakdown == []


def test_get_user_monthly_buckets_by_ct_date_not_utc():
    """A 9k step row at 2026-05-01T02:30 UTC bucketed to CT 2026-04-30,
    so it must NOT count toward May 2026's monthly total."""
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) "
                "VALUES (1, '2026-05-01T02:30:00', 9000)"
            )
        )

    with engine.connect() as conn:
        result = svc.get_user_monthly(conn, "alice", date(2026, 5, 1))

    assert result.monthly_total == 0


def test_get_user_monthly_rank_uses_dense_rank_within_month():
    """Alice 12000, Bob 8000 in May → Alice #1, Bob #2."""
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) VALUES "
                "(1, '2026-05-15T18:00:00', 12000), "
                "(2, '2026-05-15T18:00:00', 8000)"
            )
        )

    with engine.connect() as conn:
        alice = svc.get_user_monthly(conn, "alice", date(2026, 5, 1))
        bob = svc.get_user_monthly(conn, "bob", date(2026, 5, 1))

    assert alice.rank_this_month == 1
    assert bob.rank_this_month == 2


def test_get_user_monthly_unknown_user_raises_user_not_found():
    engine = _engine()
    with engine.connect() as conn:
        with pytest.raises(svc.UserNotFound) as excinfo:
            svc.get_user_monthly(conn, "ghost", date(2026, 5, 1))

    assert excinfo.value.username == "ghost"
```

- [ ] **Step 2: Run the new test file, expect collection error or test failure**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_steps_monthly.py -v
```

Expected: 5 failures, all complaining `AttributeError: module 'backend.app.services.steps' has no attribute 'get_user_monthly'`.

- [ ] **Step 3: Add `_month_bounds` helper near the other date helpers**

Edit `backend/app/services/steps.py`. Find the line `def _iso_week_bounds(week_start: date) -> tuple[date, date]:`. Insert this helper directly above it:

```python
def _month_bounds(month_start: date) -> tuple[date, date]:
    """Return (first_of_month, last_of_month_inclusive). Caller passes
    a date that is the 1st of the desired CT month; we re-anchor
    defensively so callers can pass any in-month date if they want."""
    first = month_start.replace(day=1)
    # Walk forward to the next 1st, then back one day. Avoids the
    # 28/29/30/31 special-cases entirely.
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    last = next_first - timedelta(days=1)
    return first, last
```

- [ ] **Step 4: Implement `get_user_monthly` directly below `get_user_weekly`**

Edit `backend/app/services/steps.py`. Find the closing line of `get_user_weekly` (`return UserWeeklyResponse(...)` followed by a blank line). Add this function right after:

```python
def get_user_monthly(
    conn: Connection, username: str, month_start: date
) -> "UserMonthlyResponse":
    """One user's stats for a single CT calendar month.

    Mirrors get_user_weekly: walk all per-CT-day MAX totals in the
    month for ranking, plus per-day breakdown of just this user's
    days that actually had data (no zero-filled gaps, matching the
    weekly endpoint's behavior on missing days)."""
    from backend.app.schemas.steps import UserMonthlyResponse

    user_id, _join_date = _lookup_user(conn, username)
    start, end = _month_bounds(month_start)
    rows = _daily_totals_in_range(conn, start, end)

    monthly_totals: dict[int, int] = defaultdict(int)
    user_daily: list[tuple[date, int]] = []
    for uid, d, total in rows:
        monthly_totals[uid] += total
        if uid == user_id:
            user_daily.append((d, total))

    rank = _rank_of_user(monthly_totals, user_id)
    user_daily.sort(key=lambda x: x[0])

    daily_breakdown = [
        DailyTotal(date=d, total=t) for d, t in user_daily
    ]

    return UserMonthlyResponse(
        username=username,
        month_start=start,
        month_end=end,
        monthly_total=monthly_totals.get(user_id, 0),
        rank_this_month=rank,
        daily_breakdown=daily_breakdown,
    )
```

Note: the `from backend.app.schemas.steps import UserMonthlyResponse` inside the function avoids modifying the existing top-of-file imports block (which already imports several schemas) and avoids any chance of a circular import. The other service functions follow the same module-top import convention; do NOT add `UserMonthlyResponse` to the top imports — the local import is the load-bearing pattern.

- [ ] **Step 5: Run the test file again, expect all 5 to pass**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_steps_monthly.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Run the full backend suite to confirm no regressions**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/ -v
```

Expected: all green (test count went up by 5 from baseline).

## Task 2.3 — Route: `GET /api/steps/users/{username}/monthly`

**Files:**
- Modify: `backend/app/routes/steps.py`
- Modify: `backend/tests/test_steps_monthly.py` (add HTTP-level tests)

- [ ] **Step 1: Add the failing HTTP test cases at the bottom of `test_steps_monthly.py`**

Append to `backend/tests/test_steps_monthly.py`:

```python
from fastapi.testclient import TestClient

from backend.app import db, main


def test_route_user_monthly_returns_200_and_correct_shape(monkeypatch):
    engine = _engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO steps (user_id, timestamp, total) "
                "VALUES (1, '2026-05-24T02:00:00', 9000)"
            )
        )

    response = TestClient(main.app).get(
        "/api/steps/users/alice/monthly?month=2026-05"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["month_start"] == "2026-05-01"
    assert body["month_end"] == "2026-05-31"
    assert body["monthly_total"] == 9000
    assert body["rank_this_month"] == 1
    assert body["daily_breakdown"] == [
        {"date": "2026-05-23", "total": 9000}
    ]


def test_route_user_monthly_defaults_to_current_ct_month(monkeypatch):
    """No ?month= param → service is called with the current CT month."""
    engine = _engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/steps/users/alice/monthly")
    assert response.status_code == 200
    body = response.json()
    # Don't pin to a specific month (test runs at any time); just check shape.
    assert body["username"] == "alice"
    assert "month_start" in body and "month_end" in body
    assert body["monthly_total"] == 0


def test_route_user_monthly_returns_404_for_unknown_user(monkeypatch):
    engine = _engine()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get(
        "/api/steps/users/ghost/monthly?month=2026-05"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"
```

- [ ] **Step 2: Run the new HTTP tests, expect 3 failures (404 from FastAPI: route not registered)**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_steps_monthly.py -v -k route
```

Expected: 3 failures with `404 Not Found` (route not yet registered).

- [ ] **Step 3: Add the route handler in `backend/app/routes/steps.py`**

Open `backend/app/routes/steps.py`. Add `UserMonthlyResponse` to the schema import block at the top:

```python
from backend.app.schemas.steps import (
    CreateStepRequest,
    CreateStepResponse,
    GlobalDailyResponse,
    GlobalSummaryResponse,
    GlobalWeeklyResponse,
    UserDailyResponse,
    UserMonthlyResponse,  # NEW
    UserSummaryResponse,
    UserWeeklyResponse,
)
```

Then add this new route handler directly below the existing `user_weekly` handler (which ends with `except svc.UserNotFound as e: raise _user_not_found(e.username) from e`):

```python
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
```

- [ ] **Step 4: Run all monthly tests, expect 8 passing**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_steps_monthly.py -v
```

Expected: 8 passed (5 service + 3 route).

- [ ] **Step 5: Run full suite for regressions**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/ -v
```

Expected: all green.

## Task 2.4 — Schema: `ProfileListEntry` + `ProfileListResponse`

**Files:**
- Create: `backend/app/schemas/profiles.py`

- [ ] **Step 1: Create the new schema module**

Create `backend/app/schemas/profiles.py`:

```python
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
```

- [ ] **Step 2: Verify imports**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/python -c \
  "from backend.app.schemas.profiles import ProfileListEntry, ProfileListResponse; print('ok')"
```

Expected: `ok`.

## Task 2.5 — Service: `list_profiles`

**Files:**
- Create: `backend/app/services/profiles.py`
- Test: `backend/tests/test_profiles_list.py` (create)

- [ ] **Step 1: Write the failing test file**

Create `backend/tests/test_profiles_list.py`:

```python
"""Tests for the /api/profiles list endpoint and underlying service."""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app.services import profiles as svc


def _engine_with(profiles, steps):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE profiles ("
                "id integer primary key autoincrement, "
                "username text not null unique, "
                "token text not null unique, "
                "join_date text not null default (datetime('now')))"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE steps ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "timestamp text not null, "
                "total integer not null)"
            )
        )
        for p in profiles:
            conn.execute(
                text(
                    "INSERT INTO profiles (id, username, token, join_date) "
                    "VALUES (:id, :u, :t, :j)"
                ),
                p,
            )
        for s in steps:
            conn.execute(
                text(
                    "INSERT INTO steps (user_id, timestamp, total) "
                    "VALUES (:u, :ts, :t)"
                ),
                s,
            )
    return engine


def test_list_profiles_returns_alphabetical_by_username():
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "zoe",    "t": "zoe_token________________________", "j": "2026-05-20T00:00:00"},
            {"id": 2, "u": "alice",  "t": "alice_token______________________", "j": "2026-05-19T00:00:00"},
            {"id": 3, "u": "bob",    "t": "bob_token________________________", "j": "2026-05-21T00:00:00"},
        ],
        steps=[],
    )
    with engine.connect() as conn:
        result = svc.list_profiles(conn)

    usernames = [p.username for p in result.profiles]
    assert usernames == ["alice", "bob", "zoe"]


def test_list_profiles_includes_total_steps_all_time():
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "alice",  "t": "alice_token______________________", "j": "2026-05-19T00:00:00"},
        ],
        steps=[
            # Two snapshots on the same CT day → MAX(total) counted once.
            {"u": 1, "ts": "2026-05-20T18:00:00", "t": 5000},
            {"u": 1, "ts": "2026-05-20T20:00:00", "t": 9000},
            # Next CT day → its own MAX(total).
            {"u": 1, "ts": "2026-05-21T18:00:00", "t": 4000},
        ],
    )
    with engine.connect() as conn:
        result = svc.list_profiles(conn)

    assert len(result.profiles) == 1
    assert result.profiles[0].total_steps_all_time == 9000 + 4000


def test_list_profiles_zero_step_users_show_zero_total():
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "newbie", "t": "newbie_token_____________________", "j": "2026-05-25T00:00:00"},
        ],
        steps=[],
    )
    with engine.connect() as conn:
        result = svc.list_profiles(conn)

    assert result.profiles[0].total_steps_all_time == 0


def test_list_profiles_returns_empty_list_for_empty_db():
    engine = _engine_with(profiles=[], steps=[])
    with engine.connect() as conn:
        result = svc.list_profiles(conn)

    assert result.profiles == []
```

- [ ] **Step 2: Run it, expect import error**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_profiles_list.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.app.services.profiles'`.

- [ ] **Step 3: Create the service module**

Create `backend/app/services/profiles.py`:

```python
"""Service layer for /api/profiles.

The users-index endpoint joins profiles with their all-time step total.
The `total_steps_all_time` calculation mirrors `get_user_summary` in
services/steps.py — per-CT-day MAX(total), summed across all days —
so the number matches what the Profile page already shows."""

from collections import defaultdict
from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.schemas.profiles import (
    ProfileListEntry,
    ProfileListResponse,
)
from backend.app.services.steps import OUTLIER_CAP, _ct_date


def _all_time_totals(conn: Connection) -> dict[int, int]:
    """For every user, the sum of per-CT-day MAX(total) across history.

    Matches the calculation in get_user_summary so a user's row in the
    /users index matches their Profile page's all-time stat."""
    rows = (
        conn.execute(
            text(
                "SELECT user_id, timestamp, total FROM steps "
                "WHERE total <= :cap"
            ),
            {"cap": OUTLIER_CAP},
        )
        .mappings()
        .all()
    )
    daily_max: dict[tuple[int, date], int] = {}
    for r in rows:
        d = _ct_date(r["timestamp"])
        key = (int(r["user_id"]), d)
        t = int(r["total"])
        if t > daily_max.get(key, -1):
            daily_max[key] = t
    totals: dict[int, int] = defaultdict(int)
    for (uid, _d), t in daily_max.items():
        totals[uid] += t
    return totals


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
    totals = _all_time_totals(conn)
    entries = [
        ProfileListEntry(
            username=p["username"],
            join_date=p["join_date"],
            total_steps_all_time=totals.get(int(p["id"]), 0),
        )
        for p in profile_rows
    ]
    return ProfileListResponse(profiles=entries)
```

- [ ] **Step 4: Run the service tests, expect 4 passing**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_profiles_list.py -v
```

Expected: 4 passed.

## Task 2.6 — Route: extract `/api/profiles` into a router, add `GET /api/profiles`

**Files:**
- Create: `backend/app/routes/profiles.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_profiles_list.py` (add HTTP tests)
- Verify: `backend/tests/test_profiles.py` still passes (existing tests for POST behavior)

- [ ] **Step 1: Read the current `POST /api/profiles` handler in `main.py` so we move it verbatim**

```bash
sed -n '147,189p' backend/app/main.py
```

Expected: prints the inline `create_profile` handler block — copy it for the next step.

- [ ] **Step 2: Add the failing HTTP test cases at the bottom of `test_profiles_list.py`**

Append to `backend/tests/test_profiles_list.py`:

```python
from fastapi.testclient import TestClient

from backend.app import db, main


def test_route_get_profiles_returns_200_alphabetical(monkeypatch):
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "zoe",   "t": "zoe_token________________________", "j": "2026-05-20T00:00:00"},
            {"id": 2, "u": "alice", "t": "alice_token______________________", "j": "2026-05-19T00:00:00"},
        ],
        steps=[],
    )
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/profiles")
    assert response.status_code == 200
    body = response.json()
    assert [p["username"] for p in body["profiles"]] == ["alice", "zoe"]


def test_route_get_profiles_includes_total_steps(monkeypatch):
    engine = _engine_with(
        profiles=[
            {"id": 1, "u": "alice", "t": "alice_token______________________", "j": "2026-05-19T00:00:00"},
        ],
        steps=[
            {"u": 1, "ts": "2026-05-20T18:00:00", "t": 9000},
        ],
    )
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/profiles")
    body = response.json()
    assert body["profiles"][0]["total_steps_all_time"] == 9000
```

- [ ] **Step 3: Run them, expect 404 (route not yet registered)**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_profiles_list.py::test_route_get_profiles_returns_200_alphabetical -v
```

Expected: failure with `assert 200 == 404` (the GET route doesn't exist).

- [ ] **Step 4: Create `backend/app/routes/profiles.py` with both POST (moved) and GET (new)**

Create `backend/app/routes/profiles.py`:

```python
"""HTTP layer for /api/profiles.

Read endpoint lists every user; write endpoint creates a new profile +
returns its server-issued token. The POST handler was previously
defined inline in main.py — promoted here so both verbs live in one
router and the schema stays cohesive."""

import re
import secrets
import string
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app import db
from backend.app.errors import AppError
from backend.app.schemas.profiles import ProfileListResponse
from backend.app.services import profiles as svc

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,30}$")
_TOKEN_ALPHABET = string.ascii_uppercase + string.digits
_TOKEN_GROUPS = 4
_TOKEN_GROUP_LEN = 4


class CreateProfileRequest(BaseModel):
    username: str = Field(min_length=1, max_length=30)


class ProfileResponse(BaseModel):
    """Matches the original handler exactly so existing test_profiles.py
    assertions keep passing — FastAPI serializes datetime → ISO string."""
    username: str
    token: str
    join_date: datetime


def _generate_token() -> str:
    """Grouped 4-4-4-4 uppercase token: ABCD-EFGH-IJKL-MNOP."""
    groups = [
        "".join(secrets.choice(_TOKEN_ALPHABET) for _ in range(_TOKEN_GROUP_LEN))
        for _ in range(_TOKEN_GROUPS)
    ]
    return "-".join(groups)


@router.get("", response_model=ProfileListResponse)
def list_profiles() -> ProfileListResponse:
    """Read: every user, sorted alphabetically by username."""
    with db.get_engine().connect() as conn:
        return svc.list_profiles(conn)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
def create_profile(req: CreateProfileRequest) -> ProfileResponse:
    """Write: sign up, get back a token. Username uniqueness is enforced
    at the DB level; collisions surface as 409 'username_taken'."""
    if not _USERNAME_RE.match(req.username):
        raise AppError(
            422,
            "invalid_username",
            "Username must be 1-30 characters of letters, digits, or underscore.",
        )

    token = _generate_token()
    try:
        with db.get_engine().begin() as conn:
            row = (
                conn.execute(
                    text(
                        "INSERT INTO profiles (username, token) "
                        "VALUES (:username, :token) "
                        "RETURNING username, token, join_date"
                    ),
                    {"username": req.username, "token": token},
                )
                .mappings()
                .one()
            )
    except IntegrityError as e:
        raise AppError(
            409,
            "username_taken",
            "That username is already taken.",
        ) from e

    return ProfileResponse(**dict(row))
```

- [ ] **Step 5: Wire the router into `main.py` and remove the inline POST handler**

Open `backend/app/main.py`. Find the imports block at the top (the `from backend.app.routes import ...` lines) and add:

```python
from backend.app.routes import profiles as profiles_routes
```

Find the existing `app.include_router(...)` block and add:

```python
app.include_router(profiles_routes.router)
```

Then **delete** the entire inline handler block — from `class CreateProfileRequest(BaseModel):` through the end of `def create_profile(...)`. Also delete unused module-level helpers that have moved into the router: `_USERNAME_RE`, `_generate_token`, `_TOKEN_*` constants. Check that nothing else in `main.py` still references them with:

```bash
grep -n "_USERNAME_RE\|_generate_token\|_TOKEN" backend/app/main.py
```

Expected: no matches. If any remain, they're orphans — delete them.

- [ ] **Step 6: Run the profiles tests**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_profiles_list.py backend/tests/test_profiles.py -v
```

Expected: 6 passed (4 from list + 2 new HTTP tests). The existing `test_profiles.py` tests for POST behavior should still pass — the handler moved, but the route + behavior are identical.

- [ ] **Step 7: Full suite**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/ -v
```

Expected: all green.

## Task 2.7 — Extend `list_user_feed` to include recap mentions

**Files:**
- Modify: `backend/app/services/posts.py`
- Modify: `backend/tests/test_posts_routes.py`

- [ ] **Step 1: Read the current `list_user_feed` to know what we're modifying**

```bash
grep -nA 40 "def list_user_feed" backend/app/services/posts.py
```

Expected: a function that runs `SELECT ... WHERE user_id = :uid ORDER BY timestamp DESC LIMIT :n` and maps rows into `FeedPost` objects.

- [ ] **Step 2: Add two failing test cases to `test_posts_routes.py`**

Open `backend/tests/test_posts_routes.py` and find the existing per-user feed tests (`grep -n "list_user_feed\|users/" backend/tests/test_posts_routes.py` to locate). Append at the bottom:

```python
def test_user_feed_includes_recap_where_user_appears_in_top(monkeypatch):
    """A leaderboard_recap that mentions a user in details.top must
    appear in that user's feed, even if it was authored by someone else."""
    engine = _engine_with_users_and_posts()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    with engine.begin() as conn:
        # Cron attributes the recap to user_id=1 (alice). The recap
        # mentions alice AND bob (user_id=2) in details.top.
        conn.execute(
            text(
                "INSERT INTO posts "
                "(user_id, username, type, timestamp, details, body) "
                "VALUES (1, 'alice', 'leaderboard_recap', "
                "'2026-05-24T11:00:00', :details, 'Yesterday\\'s top 3')"
            ),
            {
                "details": '{"top":[{"username":"alice","total":9000},'
                           '{"username":"bob","total":7000}],"date":"2026-05-23"}'
            },
        )

    response = TestClient(main.app).get("/api/posts/users/bob")

    assert response.status_code == 200
    posts = response.json()["posts"]
    assert len(posts) == 1
    assert posts[0]["type"] == "leaderboard_recap"


def test_user_feed_excludes_recap_where_user_not_in_top(monkeypatch):
    """A recap whose details.top does NOT include the target user
    must NOT appear in their feed, even though it exists in the table."""
    engine = _engine_with_users_and_posts()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    with engine.begin() as conn:
        # Recap mentions only alice — bob is absent.
        conn.execute(
            text(
                "INSERT INTO posts "
                "(user_id, username, type, timestamp, details, body) "
                "VALUES (1, 'alice', 'leaderboard_recap', "
                "'2026-05-24T11:00:00', :details, 'Yesterday\\'s top 3')"
            ),
            {
                "details": '{"top":[{"username":"alice","total":9000}],'
                           '"date":"2026-05-23"}'
            },
        )

    response = TestClient(main.app).get("/api/posts/users/bob")

    assert response.status_code == 200
    posts = response.json()["posts"]
    assert posts == []


def test_user_feed_dedupes_recap_authored_by_target(monkeypatch):
    """If cron attributes the recap to user X AND X is in details.top,
    the post should appear exactly once in X's feed — not twice."""
    engine = _engine_with_users_and_posts()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO posts "
                "(user_id, username, type, timestamp, details, body) "
                "VALUES (1, 'alice', 'leaderboard_recap', "
                "'2026-05-24T11:00:00', :details, 'Yesterday\\'s top 3')"
            ),
            {
                "details": '{"top":[{"username":"alice","total":9000}],'
                           '"date":"2026-05-23"}'
            },
        )

    response = TestClient(main.app).get("/api/posts/users/alice")

    posts = response.json()["posts"]
    assert len(posts) == 1
```

If `_engine_with_users_and_posts` isn't already in scope at the bottom of the file (some test modules define it earlier; check with `grep -n "_engine_with_users_and_posts" backend/tests/test_posts_routes.py`), look at how the existing per-user feed tests in the file set up their engine and reuse that pattern verbatim.

- [ ] **Step 3: Run the new tests, expect failures (only authored posts appear today)**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_posts_routes.py -v -k user_feed_
```

Expected: 2 failures (`includes_recap`, `dedupes_recap`) — they fail because the current `WHERE user_id = uid` filter doesn't pull in recaps mentioning the user. `excludes_recap_where_user_not_in_top` passes accidentally for the wrong reason (the recap *is* in the DB but the current query already excludes it, so the assertion `posts == []` holds).

- [ ] **Step 4: Replace `list_user_feed` to merge authored + mentioning recaps**

Open `backend/app/services/posts.py`. Find `def list_user_feed(...)` and replace its body with:

```python
def list_user_feed(
    conn: Connection,
    username: str,
    limit: Optional[int] = None,
) -> FeedResponse:
    """Posts that mention `username`: the union of (a) posts whose
    user_id matches and (b) leaderboard_recap posts whose details.top
    list contains the username. Sorted newest-first, deduped by id,
    clamped to `limit` (or MAX_FEED_LIMIT)."""
    import json as _json

    user_id, _ = _lookup_user(conn, username)
    n = _clamped_limit(limit)

    # Branch 1 — posts the user is the row-owner of (their milestones,
    # any future authored content). We over-fetch by `n` and merge.
    authored_rows = (
        conn.execute(
            text(
                "SELECT id, user_id, username, type, timestamp, "
                "details, body FROM posts "
                "WHERE user_id = :uid "
                "ORDER BY timestamp DESC, id DESC "
                "LIMIT :n"
            ),
            {"uid": user_id, "n": n},
        )
        .mappings()
        .all()
    )

    # Branch 2 — every leaderboard_recap. Recap row count is bounded
    # by app age in days (one per day), so an unfiltered fetch is fine.
    # We re-filter in Python so SQLite (test backend) doesn't need
    # Postgres-only jsonb operators.
    recap_rows = (
        conn.execute(
            text(
                "SELECT id, user_id, username, type, timestamp, "
                "details, body FROM posts "
                "WHERE type = 'leaderboard_recap' "
                "ORDER BY timestamp DESC, id DESC"
            )
        )
        .mappings()
        .all()
    )

    def _mentions(raw_details, target: str) -> bool:
        if raw_details is None:
            return False
        d = _json.loads(raw_details) if isinstance(raw_details, str) else raw_details
        top = d.get("top") if isinstance(d, dict) else None
        if not isinstance(top, list):
            return False
        return any(
            isinstance(e, dict) and e.get("username") == target for e in top
        )

    mentioning = [r for r in recap_rows if _mentions(r["details"], username)]

    by_id: dict[int, dict] = {}
    for r in authored_rows:
        by_id[int(r["id"])] = dict(r)
    for r in mentioning:
        by_id.setdefault(int(r["id"]), dict(r))

    merged = sorted(
        by_id.values(),
        key=lambda r: (r["timestamp"], r["id"]),
        reverse=True,
    )[:n]

    posts = [
        FeedPost(
            id=int(r["id"]),
            user_id=int(r["user_id"]),
            username=r["username"],
            type=r["type"],
            timestamp=r["timestamp"],
            details=(
                _json.loads(r["details"])
                if isinstance(r["details"], str)
                else r["details"]
            ),
            body=r["body"],
        )
        for r in merged
    ]
    return FeedResponse(posts=posts)
```

Notes for the engineer:
- `_clamped_limit(limit)` is the existing helper in this file (`grep -n _clamped_limit backend/app/services/posts.py`). If the existing function has a different name (e.g. inlines the clamp), match what's there — the contract is "clamp to MAX_FEED_LIMIT, default if None".
- `_lookup_user` is already imported/used in the file by the original `list_user_feed`. Keep using it; do NOT reintroduce a separate username→id lookup.
- The original `FeedPost(...)` construction uses these exact field names; match the existing constructor signature. If the existing call inside `list_user_feed` used a slightly different mapping (e.g. coerced `details` via a helper), preserve that — the test for the global `/feed` endpoint should not change behavior.

- [ ] **Step 5: Run the user-feed tests, expect all green**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/test_posts_routes.py -v -k user_feed
```

Expected: pass — both new mention tests + the existing authored-post tests + the dedupe test.

- [ ] **Step 6: Run the full test suite for regressions**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/ -v
```

Expected: all green.

## Task 2.8 — Commit phase A

- [ ] **Step 1: Stage only files modified by this phase**

```bash
git add backend/app/schemas/steps.py \
        backend/app/schemas/profiles.py \
        backend/app/services/steps.py \
        backend/app/services/profiles.py \
        backend/app/services/posts.py \
        backend/app/routes/steps.py \
        backend/app/routes/profiles.py \
        backend/app/main.py \
        backend/tests/test_steps_monthly.py \
        backend/tests/test_profiles_list.py \
        backend/tests/test_posts_routes.py
```

- [ ] **Step 2: Verify the staged diff matches expectations**

```bash
git diff --cached --stat
```

Expected: ~11 files. New files should be `backend/app/schemas/profiles.py`, `backend/app/services/profiles.py`, `backend/app/routes/profiles.py`, `backend/tests/test_steps_monthly.py`, `backend/tests/test_profiles_list.py`. No frontend changes staged at this point.

- [ ] **Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(backend): users-pages endpoints

Adds three endpoints powering the users-pages feature:

- GET /api/steps/users/:u/monthly — per-CT-month total, rank, and
  user-only daily breakdown. Mirrors the weekly endpoint's shape.
- GET /api/profiles — public users index, sorted alphabetical.
  total_steps_all_time matches the per-CT-day MAX-then-SUM used by
  the existing /summary endpoint, so the index and Profile page agree.
- /api/posts/users/:u — extended to include leaderboard_recap posts
  whose details.top mentions the user. Backwards-compatible for
  authored-post callers; deduped by post id.

Refactors:
- POST /api/profiles moved out of main.py into a new
  routes/profiles.py router alongside the new GET.

Test count: +13 (5 service + 3 route monthly, 4 service + 2 route
profiles, 3 mentions cases on posts).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Verify the commit landed**

```bash
git log --oneline -5
```

Expected: the new commit is on top of `f47cb48 docs(spec): users index + per-user page restructure (tabs)`.

---

# Commit 3 — Frontend: Users index page

> Run `cd frontend && npm test -- --run` between tasks to keep the suite green.

## Task 3.1 — Extract `ErrorCard` to shared UI

**Files:**
- Create: `frontend/src/components/ui/ErrorCard.tsx`
- Modify: `frontend/src/pages/Leaderboard.tsx`
- Modify: `frontend/src/pages/Feed.tsx`

> Both Leaderboard and Feed currently define their own `ErrorCard`. Extract once, import twice. No behavior change.

- [ ] **Step 1: Create the shared component**

Create `frontend/src/components/ui/ErrorCard.tsx`:

```tsx
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import { ApiError } from '@/api/client';

interface ErrorCardProps {
  error: unknown;
  onRetry: () => void;
  fallbackMessage?: string;
}

export default function ErrorCard({
  error,
  onRetry,
  fallbackMessage = 'Could not load this content.',
}: ErrorCardProps) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : fallbackMessage;
  return (
    <Card className="border-destructive/40 bg-destructive/5">
      <p className="text-destructive text-sm">{message}</p>
      <Button variant="secondary" className="mt-3" onClick={onRetry}>
        Try again
      </Button>
    </Card>
  );
}
```

- [ ] **Step 2: Replace `ErrorCard` in `Leaderboard.tsx`**

Open `frontend/src/pages/Leaderboard.tsx`. Add to the imports:

```tsx
import ErrorCard from '@/components/ui/ErrorCard';
```

Then **delete** the local `function ErrorCard(...)` definition entirely. Find each `<ErrorCard error={...} onRetry={...} />` usage and pass `fallbackMessage="Could not load the leaderboard."`:

```tsx
<ErrorCard
  error={query.error}
  onRetry={() => query.refetch()}
  fallbackMessage="Could not load the leaderboard."
/>
```

- [ ] **Step 3: Replace `ErrorCard` in `Feed.tsx`**

Open `frontend/src/pages/Feed.tsx`. Same swap as Step 2:

- Add `import ErrorCard from '@/components/ui/ErrorCard';`
- Delete local `function ErrorCard(...)` definition
- Update the usage site to pass `fallbackMessage="Could not load the feed."`

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend && npm test -- --run
```

Expected: all existing tests pass (this is a pure refactor; visible behavior is unchanged because `fallbackMessage` defaults match).

## Task 3.2 — Extract `RowListSkeleton`

**Files:**
- Create: `frontend/src/components/ui/RowListSkeleton.tsx`
- Modify: `frontend/src/pages/Leaderboard.tsx`

- [ ] **Step 1: Create the shared skeleton**

Create `frontend/src/components/ui/RowListSkeleton.tsx`:

```tsx
import Card from '@/components/ui/AppCard';

interface RowListSkeletonProps {
  rows?: number;
}

export default function RowListSkeleton({ rows = 6 }: RowListSkeletonProps) {
  return (
    <Card>
      <ul>
        {Array.from({ length: rows }).map((_, i) => (
          <li
            key={i}
            className="flex items-center gap-4 py-3 border-b border-border/60 last:border-b-0"
          >
            <span className="h-3 w-8 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 flex-1 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 w-16 bg-muted/60 rounded animate-pulse" />
          </li>
        ))}
      </ul>
    </Card>
  );
}
```

- [ ] **Step 2: Swap in `Leaderboard.tsx`**

Open `frontend/src/pages/Leaderboard.tsx`. Add:

```tsx
import RowListSkeleton from '@/components/ui/RowListSkeleton';
```

Delete the local `LeaderboardSkeleton` function. Replace `<LeaderboardSkeleton />` usages with `<RowListSkeleton />`.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npm test -- --run
```

Expected: all tests pass.

## Task 3.3 — API client: `getProfiles()`

**Files:**
- Modify: `frontend/src/api/profiles.ts`

- [ ] **Step 1: Inspect current file**

```bash
cat frontend/src/api/profiles.ts
```

Expected: only the `createProfile` wrapper.

- [ ] **Step 2: Add the list types and wrapper**

Open `frontend/src/api/profiles.ts`. Add to the top, below the existing `import { apiFetch }`:

```ts
export interface ProfileListEntry {
  username: string;
  join_date: string;
  total_steps_all_time: number;
}

export interface ProfileListResponse {
  profiles: ProfileListEntry[];
}

export function getProfiles(): Promise<ProfileListResponse> {
  return apiFetch<ProfileListResponse>('/profiles');
}
```

Leave the existing `Profile` interface and `createProfile` function untouched.

- [ ] **Step 3: TypeScript-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

## Task 3.4 — Page: `Users.tsx`

**Files:**
- Create: `frontend/src/pages/Users.tsx`
- Test: `frontend/src/__tests__/Users.test.tsx` (create)

- [ ] **Step 1: Write the failing component test**

Create `frontend/src/__tests__/Users.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Users from '@/pages/Users';
import * as profilesApi from '@/api/profiles';

function renderUsers() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/users']}>
        <Users />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Users page', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders profiles alphabetically', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      profiles: [
        { username: 'alice', join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 9000 },
        { username: 'bob',   join_date: '2026-05-20T00:00:00Z', total_steps_all_time: 4000 },
      ],
    });

    renderUsers();
    await waitFor(() => expect(screen.getByText('alice')).toBeInTheDocument());
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.getByText('9,000')).toBeInTheDocument();
  });

  it('each row links to /u/<username>', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      profiles: [
        { username: 'alice', join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 0 },
      ],
    });

    renderUsers();
    const link = await screen.findByRole('link', { name: /alice/ });
    expect(link).toHaveAttribute('href', '/u/alice');
  });

  it('shows empty state when there are no users', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({ profiles: [] });

    renderUsers();
    await waitFor(() => expect(screen.getByText(/no users yet/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run it, expect import failure**

```bash
cd frontend && npm test -- --run Users.test
```

Expected: failure with `Cannot find module '@/pages/Users'` (or similar — the file doesn't exist yet).

- [ ] **Step 3: Create the page**

Create `frontend/src/pages/Users.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import ErrorCard from '@/components/ui/ErrorCard';
import PageHeader from '@/components/ui/PageHeader';
import RowListSkeleton from '@/components/ui/RowListSkeleton';
import { getProfiles, type ProfileListEntry } from '@/api/profiles';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function UserRow({ profile }: { profile: ProfileListEntry }) {
  return (
    <li className="border-b border-border/60 last:border-b-0">
      <Link
        to={`/u/${encodeURIComponent(profile.username)}`}
        className="flex items-center gap-4 py-3 hover:text-primary transition-colors"
      >
        <span className="font-medium flex-1 min-w-0 truncate">
          {profile.username}
        </span>
        <span className="font-mono tabular-nums">
          {formatNumber(profile.total_steps_all_time)}
        </span>
      </Link>
    </li>
  );
}

export default function Users() {
  const query = useQuery({
    queryKey: ['profiles', 'list'],
    queryFn: getProfiles,
    staleTime: 60_000,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Users" description="Everyone walking." />

      {query.isPending ? (
        <RowListSkeleton />
      ) : query.isError ? (
        <ErrorCard
          error={query.error}
          onRetry={() => query.refetch()}
          fallbackMessage="Could not load the users list."
        />
      ) : query.data.profiles.length === 0 ? (
        <Card>
          <EmptyState message="No users yet." />
        </Card>
      ) : (
        <Card>
          <ul>
            {query.data.profiles.map((p) => (
              <UserRow key={p.username} profile={p} />
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run the new test file, expect pass**

```bash
cd frontend && npm test -- --run Users.test
```

Expected: 3 passed.

## Task 3.5 — Route + nav

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/AppLayout.tsx`
- Modify: `frontend/src/__tests__/smoke.test.tsx`

- [ ] **Step 1: Add the route**

Open `frontend/src/App.tsx`. Add the import:

```tsx
import Users from '@/pages/Users';
```

In the `<Route element={<AppLayout />}>` group, add:

```tsx
<Route path="/users" element={<Users />} />
```

so the block ends up looking like:

```tsx
<Route element={<AppLayout />}>
  <Route path="/feed" element={<Feed />} />
  <Route path="/users" element={<Users />} />
  <Route path="/leaderboard" element={<Leaderboard />} />
  <Route path="/u/:username" element={<Profile />} />
  <Route path="/db" element={<DbExplorer />} />
</Route>
```

- [ ] **Step 2: Add nav entries (top + bottom)**

Open `frontend/src/components/layout/AppLayout.tsx`. In the imports from `lucide-react`, add `Users`:

```tsx
import { Database, Rss, Trophy, Users } from 'lucide-react';
```

In the top-nav `<nav className="hidden sm:flex ...">` block, insert between Leaderboard and Database:

```tsx
<NavLink to="/users" className={topNavClass}>
  Users
</NavLink>
```

In the bottom mobile pill (`<div className="glass-bar ...">`), insert between Leaderboard and Database:

```tsx
<BottomNavItem
  to="/users"
  icon={<Users size={18} strokeWidth={1.75} />}
  label="Users"
/>
```

- [ ] **Step 3: Add `/users` to the smoke test**

Open `frontend/src/__tests__/smoke.test.tsx`. Find the route array (around line 22 — `['/db', ...]`) and insert `'/users'` in alphabetical order with the rest:

```tsx
const routes = [
  '/db',
  '/feed',
  '/leaderboard',
  '/users',
];
```

(Adjust to whatever the existing array shape is — preserve the test's iteration logic. The point is: render each route through the App component and confirm it doesn't throw.)

- [ ] **Step 4: Run the smoke test + Users test together**

```bash
cd frontend && npm test -- --run smoke Users.test
```

Expected: both files pass.

- [ ] **Step 5: Run the full frontend suite**

```bash
cd frontend && npm test -- --run
```

Expected: all green.

## Task 3.6 — Commit phase B

- [ ] **Step 1: Stage**

```bash
git add frontend/src/components/ui/ErrorCard.tsx \
        frontend/src/components/ui/RowListSkeleton.tsx \
        frontend/src/pages/Leaderboard.tsx \
        frontend/src/pages/Feed.tsx \
        frontend/src/api/profiles.ts \
        frontend/src/pages/Users.tsx \
        frontend/src/App.tsx \
        frontend/src/components/layout/AppLayout.tsx \
        frontend/src/__tests__/smoke.test.tsx \
        frontend/src/__tests__/Users.test.tsx
```

- [ ] **Step 2: Diff check**

```bash
git diff --cached --stat
```

Expected: 10 files. No backend, no Profile.tsx changes.

- [ ] **Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(frontend): /users index page + nav

Adds the new Users page:
- /users route listing every profile alphabetically with their
  all-time step total. Each row links to /u/<username>.
- "Users" entry added to both top nav (desktop) and bottom pill
  (mobile), between Leaderboard and Database.

Refactors:
- ErrorCard extracted to components/ui/ (shared by Feed,
  Leaderboard, Users).
- LeaderboardSkeleton extracted/renamed to RowListSkeleton in
  components/ui/ (shared by Leaderboard and Users).

Smoke test updated to include /users.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

# Commit 4 — Frontend: Profile tabs + monthly card

> The biggest change. Run `cd frontend && npm test -- --run` between tasks.

## Task 4.1 — Extract post renderers to `components/feed/`

**Files:**
- Create: `frontend/src/components/feed/MilestonePost.tsx`
- Create: `frontend/src/components/feed/RecapPost.tsx`
- Create: `frontend/src/components/feed/GenericPost.tsx`
- Create: `frontend/src/components/feed/FeedSkeleton.tsx`
- Modify: `frontend/src/pages/Feed.tsx`

> Today these four components live inline in `Feed.tsx`. Move them out so `FeedPanel` (added in Task 4.6) can reuse them.

- [ ] **Step 1: Inspect existing inline definitions in Feed.tsx**

```bash
grep -n "^function MilestonePost\|^function RecapPost\|^function GenericPost\|^function FeedSkeleton" frontend/src/pages/Feed.tsx
```

Expected: 4 function declarations.

- [ ] **Step 2: Create `MilestonePost.tsx`**

Copy the inline `function MilestonePost({ post }: { post: FeedPost }) { ... }` block into `frontend/src/components/feed/MilestonePost.tsx`. Wrap as a default export and pull its imports up:

```tsx
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';

export default function MilestonePost({ post }: { post: FeedPost }) {
  return (
    <Card>
      <div className="flex items-baseline gap-3">
        <Link
          to={`/u/${encodeURIComponent(post.username)}`}
          className="font-medium hover:text-primary transition-colors"
        >
          @{post.username}
        </Link>
        <span className="text-muted-foreground">
          {post.body ?? 'hit a milestone'}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}
```

- [ ] **Step 3: Create `RecapPost.tsx`**

Create `frontend/src/components/feed/RecapPost.tsx` with the same extraction pattern. Copy the existing inline `function RecapPost(...)` body verbatim and add the same imports as Step 2 (omit `formatPostedAt` if unused; check). Add `function formatNumber(n: number)` at the top if the original used it — `grep -A 2 "formatNumber" frontend/src/pages/Feed.tsx` to confirm.

```tsx
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

export default function RecapPost({ post }: { post: FeedPost }) {
  const top = post.details?.top ?? [];
  return (
    <Card className="bg-accent/10">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h3 className="font-display text-xl tracking-tight">
          Yesterday&rsquo;s top 3
        </h3>
        <span className="label-mono text-muted-foreground">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
      <ol className="space-y-2">
        {top.map((entry, i) => (
          <li
            key={entry.username}
            className="flex items-baseline gap-3"
          >
            <span className="label-mono w-6 shrink-0 text-muted-foreground">
              #{i + 1}
            </span>
            <Link
              to={`/u/${encodeURIComponent(entry.username)}`}
              className="font-medium hover:text-primary transition-colors flex-1 min-w-0 truncate"
            >
              @{entry.username}
            </Link>
            <span className="font-mono tabular-nums">
              {formatNumber(entry.total)}
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}
```

- [ ] **Step 4: Create `GenericPost.tsx`**

Create `frontend/src/components/feed/GenericPost.tsx`:

```tsx
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';

export default function GenericPost({ post }: { post: FeedPost }) {
  return (
    <Card>
      <div className="flex items-baseline gap-3">
        <Link
          to={`/u/${encodeURIComponent(post.username)}`}
          className="font-medium hover:text-primary transition-colors"
        >
          @{post.username}
        </Link>
        <span className="text-muted-foreground">
          {post.body ?? `posted (${post.type})`}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}
```

- [ ] **Step 5: Create `FeedSkeleton.tsx`**

Create `frontend/src/components/feed/FeedSkeleton.tsx`:

```tsx
import Card from '@/components/ui/AppCard';

export default function FeedSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <div className="flex items-baseline gap-3">
            <span className="h-3 w-20 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 flex-1 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 w-12 bg-muted/60 rounded animate-pulse" />
          </div>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Replace inline definitions in `Feed.tsx` with imports**

Open `frontend/src/pages/Feed.tsx`. Delete the inline `MilestonePost`, `RecapPost`, `GenericPost`, `FeedSkeleton` definitions and the unused-after-extraction `formatNumber` helper (if it's now unused at the top level — check usage in the remaining file body). Add at the top:

```tsx
import FeedSkeleton from '@/components/feed/FeedSkeleton';
import GenericPost from '@/components/feed/GenericPost';
import MilestonePost from '@/components/feed/MilestonePost';
import RecapPost from '@/components/feed/RecapPost';
```

The render logic referring to those components stays unchanged.

- [ ] **Step 7: Adjust `Feed.test.tsx` if it imports any of the inline pieces directly**

```bash
grep -n "MilestonePost\|RecapPost\|GenericPost\|FeedSkeleton" frontend/src/__tests__/Feed.test.tsx
```

Most likely the test imports `Feed` only and renders through it — no change needed. If it does pull a renderer directly, update the import path to `@/components/feed/<Name>`.

- [ ] **Step 8: Run frontend tests**

```bash
cd frontend && npm test -- --run
```

Expected: all green. This is a pure refactor.

## Task 4.2 — Extract `DailyBars` to shared UI

**Files:**
- Create: `frontend/src/components/ui/DailyBars.tsx`
- Modify: `frontend/src/pages/Profile.tsx`

- [ ] **Step 1: Verify the existing `WeeklyBars` in Profile.tsx**

```bash
grep -nA 25 "function WeeklyBars" frontend/src/pages/Profile.tsx
```

Expected: a chart that grids on `grid-cols-7`. We'll generalize to N bars.

- [ ] **Step 2: Create the extracted component**

Create `frontend/src/components/ui/DailyBars.tsx`:

```tsx
import type { DailyTotal } from '@/api/steps';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

interface DailyBarsProps {
  days: DailyTotal[];
  /** Number of grid columns; defaults to days.length, capped to keep
   *  Tailwind utility classes simple. Use 7 for a week, 30/31 for a month. */
  cols?: number;
}

export default function DailyBars({ days, cols }: DailyBarsProps) {
  const n = cols ?? days.length;
  const max = Math.max(...days.map((d) => d.total), 1);
  return (
    <div
      className="grid gap-2 h-28 items-end"
      style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}
    >
      {days.map((d) => {
        const heightPct = (d.total / max) * 100;
        return (
          <div
            key={d.date}
            className="flex flex-col items-center gap-1.5 h-full"
            title={`${d.date}: ${formatNumber(d.total)}`}
          >
            <div className="flex-1 w-full flex items-end">
              <div
                className="w-full bg-primary/70 rounded-t"
                style={{ height: `${Math.max(heightPct, 2)}%` }}
                aria-label={`${d.date}: ${formatNumber(d.total)} steps`}
              />
            </div>
            <span className="label-mono text-[10px] text-muted-foreground">
              {d.date.slice(-2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
```

Note: we switch from Tailwind's `grid-cols-7` to an inline `gridTemplateColumns` style so the same component handles both 7-bar weekly and 28–31-bar monthly without listing every breakpoint class. The behavior at 7 bars matches the prior implementation visually.

- [ ] **Step 3: Update Profile.tsx to import `DailyBars` and drop the local copy**

Open `frontend/src/pages/Profile.tsx`. Add:

```tsx
import DailyBars from '@/components/ui/DailyBars';
```

Delete the local `function WeeklyBars(...)` block. In `ThisWeekCard`, replace `<WeeklyBars days={data.daily_breakdown} />` with `<DailyBars days={data.daily_breakdown} cols={7} />`.

- [ ] **Step 4: Run tests**

```bash
cd frontend && npm test -- --run
```

Expected: all green. The existing Profile tests still pass because `DailyBars cols={7}` renders identically to the old `WeeklyBars`.

## Task 4.3 — API client: `getUserMonthly`

**Files:**
- Modify: `frontend/src/api/steps.ts`

- [ ] **Step 1: Add the type and wrapper**

Open `frontend/src/api/steps.ts`. Below `UserWeeklyResponse`, add:

```ts
export interface UserMonthlyResponse {
  username: string;
  month_start: string;
  month_end: string;
  monthly_total: number;
  rank_this_month: number | null;
  daily_breakdown: DailyTotal[];
}
```

Below `getUserWeekly`, add:

```ts
export function getUserMonthly(
  username: string,
  month?: string,
): Promise<UserMonthlyResponse> {
  const qs = month ? `?month=${encodeURIComponent(month)}` : '';
  return apiFetch<UserMonthlyResponse>(
    `/steps/users/${encodeURIComponent(username)}/monthly${qs}`,
  );
}
```

- [ ] **Step 2: TypeScript-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

## Task 4.4 — Restructure `Profile.tsx` with tabs

**Files:**
- Modify: `frontend/src/pages/Profile.tsx`

> Big rewrite. Keep all existing card components (`StatCard`, `StatStrip`, `ThisWeekCard`, `TodayCard`, `Header`, `NotFoundView`, `ErrorView`, `StatStripSkeleton`, `CardSkeleton`). Add `ThisMonthCard`, `SummaryPanel`, `FeedPanel`. Replace the top-level `Profile()` body to gate on the active tab.

- [ ] **Step 1: Add new imports to Profile.tsx**

```tsx
import { useSearchParams } from 'react-router-dom';
import TabStrip from '@/components/ui/TabStrip';
import EmptyState from '@/components/ui/EmptyState';
import FeedSkeleton from '@/components/feed/FeedSkeleton';
import GenericPost from '@/components/feed/GenericPost';
import MilestonePost from '@/components/feed/MilestonePost';
import RecapPost from '@/components/feed/RecapPost';
import ErrorCard from '@/components/ui/ErrorCard';
import { getUserFeed, type FeedPost } from '@/api/posts';
import {
  getUserMonthly,
  type UserMonthlyResponse,
} from '@/api/steps';
```

Keep all existing imports — these are additions.

- [ ] **Step 2: Add `ThisMonthCard` component**

Insert directly after `ThisWeekCard`:

```tsx
function ThisMonthCard({ data }: { data: UserMonthlyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="font-display text-2xl tracking-tight">This month</h2>
        <span className="label-mono text-muted-foreground">
          {formatNumber(data.monthly_total)} steps ·{' '}
          {data.rank_this_month !== null ? `#${data.rank_this_month}` : '—'}
        </span>
      </div>
      <DailyBars days={data.daily_breakdown} cols={data.daily_breakdown.length || 1} />
    </Card>
  );
}
```

- [ ] **Step 3: Replace the top-level `Profile()` body with a tab gate**

Replace the entire `export default function Profile() { ... }` body. The new shape:

```tsx
const TABS = [
  { key: 'summary', label: 'Summary' },
  { key: 'feed',    label: 'Feed' },
] as const;

function currentMonthYYYYMM(): string {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  return `${yyyy}-${mm}`;
}

function SummaryPanel({ username }: { username: string }) {
  const today = currentDate();
  const month = currentMonthYYYYMM();

  const summary = useQuery({
    queryKey: ['steps', 'users', username, 'summary'],
    queryFn: () => getUserSummary(username),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });
  const daily = useQuery({
    queryKey: ['steps', 'users', username, 'daily', today],
    queryFn: () => getUserDaily(username, today),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });
  const weekly = useQuery({
    queryKey: ['steps', 'users', username, 'weekly'],
    queryFn: () => getUserWeekly(username),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });
  const monthly = useQuery({
    queryKey: ['steps', 'users', username, 'monthly', month],
    queryFn: () => getUserMonthly(username, month),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });

  return (
    <div className="space-y-6">
      {summary.isPending ? (
        <StatStripSkeleton />
      ) : summary.isError ? (
        <ErrorView error={summary.error} onRetry={() => summary.refetch()} />
      ) : (
        <StatStrip data={summary.data} />
      )}

      {daily.isPending ? (
        <CardSkeleton heightClass="h-20" />
      ) : daily.isError ? (
        <ErrorView error={daily.error} onRetry={() => daily.refetch()} />
      ) : (
        <TodayCard data={daily.data} />
      )}

      {weekly.isPending ? (
        <CardSkeleton heightClass="h-32" />
      ) : weekly.isError ? (
        <ErrorView error={weekly.error} onRetry={() => weekly.refetch()} />
      ) : (
        <ThisWeekCard data={weekly.data} />
      )}

      {monthly.isPending ? (
        <CardSkeleton heightClass="h-32" />
      ) : monthly.isError ? (
        <ErrorView error={monthly.error} onRetry={() => monthly.refetch()} />
      ) : (
        <ThisMonthCard data={monthly.data} />
      )}
    </div>
  );
}

function FeedPanel({ username }: { username: string }) {
  const query = useQuery({
    queryKey: ['posts', 'users', username, 'feed', 50],
    queryFn: () => getUserFeed(username, 50),
    enabled: !!username,
    staleTime: 30_000,
  });

  if (query.isPending) return <FeedSkeleton />;
  if (query.isError) {
    return (
      <ErrorCard
        error={query.error}
        onRetry={() => query.refetch()}
        fallbackMessage="Could not load this user's feed."
      />
    );
  }
  if (query.data.posts.length === 0) {
    return (
      <Card>
        <EmptyState message="No posts mention this user yet." />
      </Card>
    );
  }
  return (
    <div className="space-y-4">
      {query.data.posts.map((post: FeedPost) => {
        if (post.type === 'leaderboard_recap') return <RecapPost key={post.id} post={post} />;
        if (post.type === 'steps_milestone')   return <MilestonePost key={post.id} post={post} />;
        return <GenericPost key={post.id} post={post} />;
      })}
    </div>
  );
}

export default function Profile() {
  const { username = '' } = useParams<{ username: string }>();
  const [params] = useSearchParams();
  const active = params.get('tab') ?? 'summary';

  // 404 detection: hang on the summary query because every Profile
  // visit hits it regardless of which tab is active.
  const summary = useQuery({
    queryKey: ['steps', 'users', username, 'summary'],
    queryFn: () => getUserSummary(username),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });

  if (
    summary.error instanceof ApiError &&
    summary.error.code === 'user_not_found'
  ) {
    return <NotFoundView username={username} />;
  }

  return (
    <div className="space-y-6">
      <Header
        username={summary.data?.username ?? username}
        joinDate={summary.data?.join_date}
      />
      <TabStrip tabs={[...TABS]} defaultKey="summary" />
      {active === 'feed' ? (
        <FeedPanel username={username} />
      ) : (
        <SummaryPanel username={username} />
      )}
      <div className="pt-2">
        <Link
          to="/feed"
          className="label-mono text-muted-foreground hover:text-foreground border-b border-transparent hover:border-foreground transition-colors pb-0.5"
        >
          ← back to feed
        </Link>
      </div>
    </div>
  );
}
```

Note: `SummaryPanel` now runs its own copy of the `summary` query. React Query's cache dedupes by `queryKey`, so the top-level `summary` query (used for 404 detection) and `SummaryPanel`'s `summary` query share a single network request. Don't try to lift the summary into the parent and pass it down — keeping it inside the panel keeps the panel self-contained for testing.

- [ ] **Step 4: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

## Task 4.5 — Rewrite `Profile.test.tsx`

**Files:**
- Modify: `frontend/src/__tests__/Profile.test.tsx`

- [ ] **Step 1: Inspect existing tests**

```bash
cat frontend/src/__tests__/Profile.test.tsx
```

Expected: tests rendering the old non-tabbed layout.

- [ ] **Step 2: Replace with the tabbed version**

Rewrite `frontend/src/__tests__/Profile.test.tsx` entirely. Use this content (adjust the mock shapes if any field names differ from `@/api/steps` exports):

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Profile from '@/pages/Profile';
import * as stepsApi from '@/api/steps';
import * as postsApi from '@/api/posts';
import { ApiError } from '@/api/client';

function renderProfile(initialUrl = '/u/alice') {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialUrl]}>
        <Routes>
          <Route path="/u/:username" element={<Profile />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockAllSummaryQueries() {
  vi.spyOn(stepsApi, 'getUserSummary').mockResolvedValue({
    username: 'alice',
    join_date: '2026-05-19T00:00:00Z',
    total_steps_all_time: 12000,
    best_day: { date: '2026-05-23', total: 9000 },
    rank_all_time: 1,
    days_active: 2,
  });
  vi.spyOn(stepsApi, 'getUserDaily').mockResolvedValue({
    username: 'alice',
    date: '2026-05-25',
    total: 955,
    rank_today: 1,
    posts: [],
  });
  vi.spyOn(stepsApi, 'getUserWeekly').mockResolvedValue({
    username: 'alice',
    week_start: '2026-05-25',
    week_end: '2026-05-31',
    weekly_total: 955,
    rank_this_week: 1,
    daily_breakdown: [],
  });
  vi.spyOn(stepsApi, 'getUserMonthly').mockResolvedValue({
    username: 'alice',
    month_start: '2026-05-01',
    month_end: '2026-05-31',
    monthly_total: 11075,
    rank_this_month: 1,
    daily_breakdown: [],
  });
}

describe('Profile page', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('summary is the default tab', async () => {
    mockAllSummaryQueries();
    renderProfile('/u/alice');
    await waitFor(() => expect(screen.getByText(/All-time steps/i)).toBeInTheDocument());
    expect(screen.getByText('This week')).toBeInTheDocument();
    expect(screen.getByText('This month')).toBeInTheDocument();
  });

  it('renders the monthly card on the summary tab', async () => {
    mockAllSummaryQueries();
    renderProfile('/u/alice');
    await waitFor(() => expect(screen.getByText('This month')).toBeInTheDocument());
    expect(screen.getByText('11,075 steps · #1')).toBeInTheDocument();
  });

  it('feed tab renders posts from getUserFeed', async () => {
    mockAllSummaryQueries();
    vi.spyOn(postsApi, 'getUserFeed').mockResolvedValue({
      posts: [
        {
          id: 99,
          user_id: 1,
          username: 'alice',
          type: 'steps_milestone',
          timestamp: '2026-05-23T22:00:00Z',
          details: { threshold: 5000, date: '2026-05-23' },
          body: 'hit 5,000 steps',
        },
      ],
    });

    renderProfile('/u/alice?tab=feed');
    await waitFor(() => expect(screen.getByText('hit 5,000 steps')).toBeInTheDocument());
  });

  it('feed tab shows empty state when no posts mention the user', async () => {
    mockAllSummaryQueries();
    vi.spyOn(postsApi, 'getUserFeed').mockResolvedValue({ posts: [] });

    renderProfile('/u/alice?tab=feed');
    await waitFor(() =>
      expect(screen.getByText(/no posts mention this user yet/i)).toBeInTheDocument(),
    );
  });

  it('renders NotFoundView when summary returns user_not_found', async () => {
    vi.spyOn(stepsApi, 'getUserSummary').mockRejectedValue(
      new ApiError(404, 'user_not_found', 'No one named ghost'),
    );

    renderProfile('/u/ghost');
    await waitFor(() => expect(screen.getByText(/No one named ghost/i)).toBeInTheDocument());
  });

  it('clicking the Feed tab updates the URL to ?tab=feed', async () => {
    mockAllSummaryQueries();
    vi.spyOn(postsApi, 'getUserFeed').mockResolvedValue({ posts: [] });
    const user = userEvent.setup();

    renderProfile('/u/alice');
    await waitFor(() => expect(screen.getByText('This month')).toBeInTheDocument());

    await user.click(screen.getByRole('tab', { name: /feed/i }));
    await waitFor(() =>
      expect(screen.getByText(/no posts mention this user yet/i)).toBeInTheDocument(),
    );
  });
});
```

Notes for the engineer:
- `ApiError` constructor signature: check `frontend/src/api/client.ts` and match (`new ApiError(status, code, message)`).
- `TabsTrigger` from `@/components/ui/tabs` renders as `role="tab"`. If your radix/shadcn version exposes a different role, adjust the `getByRole` calls accordingly — confirm by running one test and inspecting the rendered HTML in the failure output.

- [ ] **Step 3: Run the Profile tests**

```bash
cd frontend && npm test -- --run Profile.test
```

Expected: 6 passed. If any fail, the most common causes are: (1) mock response shape doesn't match what the component reads — fix the mock to match `@/api/steps` types; (2) `role="tab"` query doesn't match the actual rendered role — use `screen.getByText` instead.

## Task 4.6 — Full frontend suite + commit phase C

- [ ] **Step 1: Run the full suite for regressions**

```bash
cd frontend && npm test -- --run
```

Expected: all green. If `Feed.test.tsx` fails because of the post-renderer extraction, the only fix should be import paths — not assertion changes.

- [ ] **Step 2: Stage**

```bash
git add frontend/src/components/feed/ \
        frontend/src/components/ui/DailyBars.tsx \
        frontend/src/pages/Feed.tsx \
        frontend/src/pages/Profile.tsx \
        frontend/src/api/steps.ts \
        frontend/src/__tests__/Profile.test.tsx \
        frontend/src/__tests__/Feed.test.tsx
```

Note: `git add frontend/src/components/feed/` will pick up all four new files in that directory.

- [ ] **Step 3: Diff check**

```bash
git diff --cached --stat
```

Expected: ~10 files (4 new in `components/feed/`, 1 new `DailyBars.tsx`, modifications to Feed/Profile/api).

- [ ] **Step 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat(frontend): /u/:username tabs + monthly card

Restructures the per-user Profile page:
- Two tabs: Summary | Feed, URL state via ?tab=summary|feed.
- Summary tab stacks StatStrip + Today + This Week + This Month
  (new). Each card has its own query, skeleton, and error/retry.
- Feed tab renders posts from /api/posts/users/:u (which now
  includes recap mentions per the backend commit) using the same
  renderers as /feed.

Refactors:
- MilestonePost, RecapPost, GenericPost, FeedSkeleton extracted
  from Feed.tsx into components/feed/ and shared with the new
  FeedPanel.
- WeeklyBars (Profile-local) extracted into components/ui/DailyBars
  and parameterized on column count so the same component renders
  the 7-bar weekly chart and the 28-31-bar monthly chart.
- Profile.test.tsx fully rewritten for the tabbed shape.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: Verify commit log**

```bash
git log --oneline -6
```

Expected: four commits on this branch, newest first: (4) feat(frontend) tabs + monthly card, (3) feat(frontend) /users index, (2) feat(backend) users-pages endpoints, (1) docs(spec) users-pages design.

---

# Final verification & PR

## Task 5.1 — Run both suites end-to-end

- [ ] **Step 1: Backend**

```bash
/Users/micahbriggs/Developer/synzoia/backend/.venv/bin/pytest backend/tests/ -v
```

Expected: all green; ~+13 tests vs. baseline.

- [ ] **Step 2: Frontend**

```bash
cd frontend && npm test -- --run
```

Expected: all green; ~+9 tests vs. baseline (3 Users + 6 Profile new/rewritten).

- [ ] **Step 3: TypeScript clean**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

## Task 5.2 — Push and open the PR

- [ ] **Step 1: Push the branch**

```bash
git push -u origin worktree-users-pages
```

- [ ] **Step 2: Open the PR via gh**

```bash
gh pr create --title "feat: users index + per-user page restructure" --body "$(cat <<'EOF'
## Summary

- New `/users` page listing every profile alphabetically with all-time step totals; row links to `/u/<username>`.
- `/u/:username` restructured into two tabs: **Summary** (StatStrip + Today + This Week + This Month) and **Feed** (posts mentioning the user).
- Backend gains three changes: new `/api/steps/users/:u/monthly`, new `/api/profiles` list, and extended `/api/posts/users/:u` to include `leaderboard_recap` posts whose `details.top` mentions the user.

Spec: `docs/superpowers/specs/2026-05-25-users-pages-design.md`
Plan: `docs/superpowers/plans/2026-05-25-users-pages.md`

## Test plan

- [x] `pytest backend/tests/ -v` — all green; +13 new test cases.
- [x] `cd frontend && npm test -- --run` — all green; +9 new test cases.
- [x] `cd frontend && npx tsc --noEmit` — no errors.
- [ ] Manual: visit `/users`, click a user, switch tabs on Profile.
- [ ] Manual: confirm a `leaderboard_recap` post appears on the profile of every user listed in its `details.top`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Capture the PR URL**

The `gh pr create` output prints the URL. Confirm CI starts running. The branch protection on `main` requires status checks before merge — let CI run, address any failures, then merge through the normal PR UI.

---

## Spec coverage check

Final mapping from spec sections to plan tasks:

| Spec section | Plan task(s) |
|---|---|
| §2 Routing & navigation | 3.5 (route + nav), 3.5 step 3 (smoke test) |
| §3.1 New monthly endpoint | 2.1 (schema), 2.2 (service + tests), 2.3 (route + tests) |
| §3.2 New profiles list endpoint | 2.4 (schema), 2.5 (service + tests), 2.6 (router + tests) |
| §3.3 Extended user feed (mentions) | 2.7 |
| §3.4 Backend tests | covered inline in each backend task |
| §4 Users index page | 3.3 (API client), 3.4 (page + tests), 3.5 (route + nav + smoke) |
| §5.1 Summary tab | 4.2 (DailyBars extract), 4.3 (API client), 4.4 (restructure incl. ThisMonthCard) |
| §5.2 Feed tab | 4.1 (renderer extract), 4.4 (FeedPanel in Profile restructure) |
| §5.3 404 handling | 4.4 (top-level summary query + NotFoundView gate retained) |
| §5.4 Frontend tests | 4.5 (Profile rewrite), 4.1 step 7 (Feed test path fix), 3.4 (Users tests) |
| §6 Error & empty states | 3.4 (Users), 4.4 (Profile per-card), 4.4 (Feed empty + error) |
| §9 Implementation order | Three commits structured exactly as 2.x / 3.x / 4.x |
