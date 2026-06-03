# Rolling windows + "Last night" fix — design

**Date:** 2026-06-02
**Status:** Approved (design)
**Scope:** backend (steps + sleep services, routes) + frontend (profile cards, leaderboard, query builders). No DB/schema/migration changes.

## Goal

1. Replace "this week" (ISO Monday–Sunday) and "this month" (calendar month) with **rolling windows** everywhere they appear — last **7** days and last **30** days, ending today (CT, inclusive) — for both steps and sleep, on both the per-user profile and the global leaderboard.
2. Relabel those views **"Last 7 days"** / **"Last 30 days"**.
3. Fix a separate off-by-one bug: the sleep **"Last night"** card queries `night_of = today` but should query `night_of = today − 1` (the night you woke from this morning).

## Why

A user's sleep/steps from a few days ago falls outside the ISO week / calendar month and shows as blank, even though the data exists (confirmed: Max's only session is `night_of 2026-05-30`; on 2026-06-02 it's outside last-night, this-ISO-week (Jun 1–7), and this-month (June), so all three cards read empty). Rolling windows keep recent data visible across week/month boundaries. The "Last night" off-by-one means a freshly-logged session never appears under "Last night."

## Context (current state)

- **Bounds helpers are duplicated**: `_iso_week_bounds` + `_month_bounds` exist in BOTH `backend/app/services/steps.py` (lines ~103–118) and `backend/app/services/sleep.py` (lines ~85–99), identical.
- **Service consumers** (both steps.py and sleep.py): `get_user_weekly`, `get_user_monthly`, `get_global_weekly`, `get_global_summary` (the summary embeds a "this week" leader). Each builds a `daily_breakdown: list[DailyTotal{date,total}]` over `[start,end]`.
- **Routes** (`routes/steps.py`, `routes/sleep.py`): weekly defaults `week_start = _iso_monday(_today())`; monthly defaults `today.replace(day=1)`, param `?month=YYYY-MM`; summary uses `_iso_monday(today)`.
- **Schemas** (`schemas/steps.py`, `schemas/sleep.py`): `UserWeeklyResponse`/`GlobalWeeklyResponse` have `week_start`, `week_end`, `daily_breakdown`; `UserMonthlyResponse` has `month_start`, `month_end`, `daily_breakdown`. **No field changes needed** — same fields, rolling values.
- **Frontend query keys** (`api/userSummaryQueries.ts`): weekly builders (`stepsWeeklyQuery`, `sleepWeeklyQuery`) bake **no date** into their key → they never refetch across days (latent bug). Monthly builders key on `month` (YYYY-MM). Daily builders key on `today`.
- **Frontend leaderboard** (`pages/Leaderboard.tsx`): steps-only, tabs `today` + `week`; weekly query key `['steps','weekly']` (no date); calls `getGlobalWeekly()` (no param). There is **no sleep leaderboard UI**.
- **`DailyBars`** (`components/ui/DailyBars.tsx`): labels each bar with `d.date.slice(-2)` (day-of-month) — works for rolling ranges as-is.
- **Sleep "Last night" card** (`pages/Profile.tsx`): uses `sleepDailyQuery(username, today)`; the daily sleep endpoint does `WHERE night_of = :date`. Since `night_of = wake_date − 1`, querying `today` targets tonight's not-yet-existent night.
- **cron** (`services/cron.py`): depends only on "yesterday" (daily) — unaffected.

## Design

### 1. Shared rolling-bounds helper (backend)

Create `backend/app/services/windows.py`:

```python
from datetime import date, timedelta

def rolling_bounds(end: date, days: int) -> tuple[date, date]:
    """Inclusive [start, end] window of `days` days ending at `end`.
    days=7 -> last 7 days; days=30 -> last 30 days."""
    return (end - timedelta(days=days - 1), end)
```

Both `steps.py` and `sleep.py` import and use it. Remove the duplicated `_iso_week_bounds` / `_month_bounds` from both (and the `_iso_monday` route helper where it was only used for these defaults).

### 2. Service functions take an `as_of` end date (backend)

`get_user_weekly`, `get_user_monthly`, `get_global_weekly`, `get_global_summary` (steps + sleep) take an `as_of: date` (the window's end, = today by default) instead of `week_start` / `month_start`:
- weekly/global-weekly/summary-week: `start, end = rolling_bounds(as_of, 7)`
- monthly: `start, end = rolling_bounds(as_of, 30)`

`daily_breakdown` is built over `[start, end]` exactly as today (7 entries for week, 30 for month). Response fields `week_start`/`week_end`/`month_start`/`month_end` now carry the rolling bounds.

### 3. Routes: `?as_of=YYYY-MM-DD` (backend)

Replace `?week_start` and `?month=YYYY-MM` on the weekly/monthly endpoints (steps + sleep, per-user + global) with an optional `?as_of: date` (default `_today()` in CT). Summary endpoints default `as_of = _today()`. This is a breaking param change; the only reader is this frontend (the iOS Shortcut only writes), so it is safe.

### 4. Frontend query keys + calls

In `api/userSummaryQueries.ts` and the `api/steps.ts` / `api/sleep.ts` fetchers:
- `stepsWeeklyQuery(u, today)` / `sleepWeeklyQuery(u, today)` → key `['steps','users',u,'weekly', today]` (add `today`). Fetch passes `?as_of=today` (or relies on default; key carries today for freshness).
- `stepsMonthlyQuery(u, today)` / `sleepMonthlyQuery(u, today)` → key `['...','monthly', today]` (replace `month` with `today`). Drop `currentMonthYYYYMM()` usage for these.
- Daily builders unchanged except sleep "Last night" (see §6).
- `pages/Profile.tsx`: pass `today` to the weekly + monthly builders (currently passes nothing / `month`). Keep parity between the prefetch (`userSummaryQueries`) and the Profile call sites.
- `pages/Leaderboard.tsx`: weekly key `['steps','weekly', today]`; `getGlobalWeekly()` may pass `?as_of=today` or rely on default.

### 5. Labels (frontend)

- Profile cards: "This week" → **"Last 7 days"**, "This month" → **"Last 30 days"** (steps + sleep).
- Leaderboard tab: "This Week" → **"Last 7 days"** (the tab key can stay `week` internally).
- `DailyBars` unchanged.

### 6. "Last night" off-by-one fix (frontend)

Add `lastNightDate(now?): string` to `lib/dates.ts` → the CT date of `today − 1` (the `night_of` of the night you woke from this morning). The sleep "Last night" card and its prefetch builder use `sleepDailyQuery(username, lastNightDate())` so their React Query keys match. Steps "Today" daily keeps `today`.

## Testing (TDD)

- **Backend**
  - `backend/tests/test_windows.py` (new): `rolling_bounds(date(2026,6,2), 7) == (date(2026,5,27), date(2026,6,2))`; `days=30` → `(2026,5,4)..(2026,6,2)`.
  - Steps + sleep service tests: a session/steps row at `as_of − 3` days IS included in the rolling week; one at `as_of − 8` is NOT; monthly includes `as_of − 20`, excludes `as_of − 35`. Use dates relative to a fixed `as_of`.
  - Route tests: `GET .../weekly?as_of=YYYY-MM-DD` and `.../monthly?as_of=...` return the rolling bounds + breakdown length (7 / 30). Update existing tests that pass `?week_start` / `?month`.
- **Frontend**
  - `userSummaryQueries` test: weekly + monthly keys include `today`; sleep daily ("last night") keys on `today − 1`.
  - Profile/Leaderboard render tests: cards labeled "Last 7 days" / "Last 30 days"; leaderboard tab "Last 7 days".

## Out of scope

- DB schema / migrations (none).
- A sleep leaderboard UI (doesn't exist; not adding it).
- cron / recap logic (daily-only, unaffected).
- Changing the daily ("Today" steps) semantics.

## Trickiest spots

- **Query-key parity**: the prefetch builders (`userSummaryQueries`) and the Profile call sites must pass the SAME date args, or prefetch warms keys the page never reads (the #46 invariant). Weekly/monthly now key on `today`; sleep "last night" keys on `today − 1`.
- **Param semantics change**: `?week_start`/`?month` → `?as_of`. Update every test that used the old params.
- **`as_of` default = CT today** on the server must match the frontend's `today` (both already CT via `_today()` / `currentDate()`).
