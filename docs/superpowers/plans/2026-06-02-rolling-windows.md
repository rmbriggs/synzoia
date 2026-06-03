# Rolling Windows + "Last night" Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ISO-week / calendar-month windows with rolling last-7 / last-30-day windows (ending today, CT, inclusive) for steps + sleep on profile + leaderboard, relabel them "Last 7 days" / "Last 30 days", and fix the sleep "Last night" off-by-one.

**Architecture:** One shared `rolling_bounds(end, days)` backend helper replaces the duplicated week/month bounds in both services; weekly/monthly/summary services take an `as_of` end date (default CT today) and the routes expose `?as_of=YYYY-MM-DD`. Frontend weekly/monthly query keys gain `today` (fixing a latent never-refetch bug), the sleep "Last night" card queries `night_of = today − 1` via a new `lastNightDate()` helper, and labels are updated. No DB/schema changes.

**Tech Stack:** FastAPI + SQLAlchemy + pytest (backend); React + @tanstack/react-query + Vitest (frontend).

---

## Setup

- [ ] **Step 0: Confirm test runners**

Backend:
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows/backend
python -m pytest -q 2>&1 | tail -5
```
Frontend (symlink node_modules, no new deps):
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows/frontend
ln -s /Users/micahbriggs/Developer/synzoia/frontend/node_modules ./node_modules
ls node_modules/.bin/vitest
```
Expected: backend suite runs; vitest path prints.

---

### Task 1: Shared `rolling_bounds` helper

**Files:**
- Create: `backend/app/services/windows.py`
- Test: `backend/tests/test_windows.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_windows.py`:
```python
from datetime import date
from backend.app.services.windows import rolling_bounds


def test_rolling_7_day_window_is_inclusive_and_ends_at_anchor():
    assert rolling_bounds(date(2026, 6, 2), 7) == (date(2026, 5, 27), date(2026, 6, 2))


def test_rolling_30_day_window():
    assert rolling_bounds(date(2026, 6, 2), 30) == (date(2026, 5, 4), date(2026, 6, 2))


def test_window_of_one_day_is_just_the_anchor():
    assert rolling_bounds(date(2026, 6, 2), 1) == (date(2026, 6, 2), date(2026, 6, 2))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_windows.py -q`
Expected: FAIL — `ModuleNotFoundError: backend.app.services.windows`.

- [ ] **Step 3: Implement the helper**

Create `backend/app/services/windows.py`:
```python
"""Shared time-window bounds for the read aggregations.

Steps and sleep both summarize activity over "this week" and "this
month". As of the rolling-windows change these are rolling windows
ending today (inclusive), not ISO weeks or calendar months — so both
services compute their bounds here and stay consistent.
"""
from datetime import date, timedelta


def rolling_bounds(end: date, days: int) -> tuple[date, date]:
    """Inclusive [start, end] window of `days` days ending at `end`.

    days=7  -> the last 7 days (end-6 .. end)
    days=30 -> the last 30 days (end-29 .. end)
    """
    return (end - timedelta(days=days - 1), end)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_windows.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add backend/app/services/windows.py backend/tests/test_windows.py
git commit -m "feat(backend): add shared rolling_bounds window helper

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Steps service → rolling windows via `as_of`

**Files:**
- Modify: `backend/app/services/steps.py`
- Test: `backend/tests/test_steps_service.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_steps_service.py` (import `date`, `timedelta`, and the service as the existing tests do — match the existing fixture/connection setup in that file for inserting step rows; the assertions below are the new behavior):
```python
def test_user_weekly_is_rolling_last_7_days(seeded_conn):
    # seeded_conn: a connection with user 'amy' having step rows on
    # as_of and as_of-3 (inside) and as_of-8 (outside). Reuse this
    # file's existing row-insert helper.
    from datetime import date, timedelta
    from backend.app.services import steps as svc
    as_of = date(2026, 6, 2)
    _insert_steps(seeded_conn, "amy", as_of, 1000)
    _insert_steps(seeded_conn, "amy", as_of - timedelta(days=3), 500)
    _insert_steps(seeded_conn, "amy", as_of - timedelta(days=8), 9999)

    resp = svc.get_user_weekly(seeded_conn, "amy", as_of)

    assert resp.week_start == as_of - timedelta(days=6)
    assert resp.week_end == as_of
    assert len(resp.daily_breakdown) == 7
    assert resp.weekly_total == 1500  # as_of-8 excluded


def test_user_monthly_is_rolling_last_30_days(seeded_conn):
    from datetime import date, timedelta
    from backend.app.services import steps as svc
    as_of = date(2026, 6, 2)
    _insert_steps(seeded_conn, "amy", as_of - timedelta(days=20), 700)
    _insert_steps(seeded_conn, "amy", as_of - timedelta(days=35), 9999)

    resp = svc.get_user_monthly(seeded_conn, "amy", as_of)

    assert resp.month_start == as_of - timedelta(days=29)
    assert resp.month_end == as_of
    assert resp.monthly_total == 700  # as_of-35 excluded
```
(If `test_steps_service.py` has no reusable `_insert_steps`/`seeded_conn`, mirror the row-insert + in-memory engine pattern already used elsewhere in that file. The KEY assertions are the rolling bounds + inclusion/exclusion.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_steps_service.py -q -k "rolling"`
Expected: FAIL — `get_user_weekly`/`get_user_monthly` still take `week_start`/`month_start` and use ISO-week/calendar-month bounds, so `week_start`/`month_start` assertions are wrong.

- [ ] **Step 3: Implement — swap bounds + rename param to `as_of`**

In `backend/app/services/steps.py`:

(a) Delete the two helpers `_month_bounds` (lines ~103–113) and `_iso_week_bounds` (lines ~116–118), and add the import near the top imports:
```python
from backend.app.services.windows import rolling_bounds
```

(b) `get_global_weekly` — change signature + bounds:
```python
def get_global_weekly(
    conn: Connection, as_of: date
) -> GlobalWeeklyResponse:
    start, end = rolling_bounds(as_of, 7)
```
(leave the rest of the function body unchanged — it already builds 7 daily entries from `start`).

(c) `get_global_summary` — change signature to `as_of` and derive both today + week from it:
```python
def get_global_summary(
    conn: Connection, as_of: date
) -> GlobalSummaryResponse:
```
then replace the today/week lines:
```python
    today_leader = _top_leader(conn, as_of, as_of)
    week_start, week_end = rolling_bounds(as_of, 7)
    this_week_leader = _top_leader(conn, week_start, week_end)
```

(d) `get_user_weekly` — signature + bounds:
```python
def get_user_weekly(
    conn: Connection, username: str, as_of: date
) -> UserWeeklyResponse:
    user_id, _join_date = _lookup_user(conn, username)
    start, end = rolling_bounds(as_of, 7)
```

(e) `get_user_monthly` — signature + bounds (30 days):
```python
def get_user_monthly(
    conn: Connection, username: str, as_of: date
) -> "UserMonthlyResponse":
```
replace `start, end = _month_bounds(month_start)` with:
```python
    start, end = rolling_bounds(as_of, 30)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_steps_service.py -q`
Expected: rolling tests PASS. Some existing service tests that asserted ISO-week/calendar-month bounds or removed-helper names will now fail — fix them in Step 5.

- [ ] **Step 5: Update existing steps service tests + commit**

In `backend/tests/test_steps_service.py`, update any test that:
- imported/called `_iso_week_bounds` or `_month_bounds` → delete or rewrite against `rolling_bounds` (now in `windows.py`).
- called `get_user_weekly(conn, user, some_monday)` / `get_user_monthly(conn, user, first_of_month)` → pass an `as_of` date and assert rolling bounds (`as_of-6..as_of`, `as_of-29..as_of`).

Run: `cd backend && python -m pytest tests/test_steps_service.py -q`
Expected: all PASS.

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add backend/app/services/steps.py backend/tests/test_steps_service.py
git commit -m "feat(backend): steps weekly/monthly/summary use rolling windows via as_of

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Sleep service → rolling windows via `as_of`

**Files:**
- Modify: `backend/app/services/sleep.py`
- Test: `backend/tests/test_sleep_service.py` (or wherever sleep read aggregations are tested)

- [ ] **Step 1: Write the failing test**

Add rolling tests mirroring Task 2 but for sleep (sleep rows keyed by `night_of`, value `duration_min`). Use the sleep test file's existing insert helper:
```python
def test_sleep_user_weekly_is_rolling_last_7_days(seeded_conn):
    from datetime import date, timedelta
    from backend.app.services import sleep as svc
    as_of = date(2026, 6, 2)
    _insert_sleep(seeded_conn, "amy", night_of=as_of - timedelta(days=2), duration_min=400)
    _insert_sleep(seeded_conn, "amy", night_of=as_of - timedelta(days=8), duration_min=999)

    resp = svc.get_user_weekly(seeded_conn, "amy", as_of)

    assert resp.week_start == as_of - timedelta(days=6)
    assert resp.week_end == as_of
    assert len(resp.daily_breakdown) == 7
    assert resp.weekly_total == 400  # as_of-8 excluded


def test_sleep_user_monthly_is_rolling_last_30_days(seeded_conn):
    from datetime import date, timedelta
    from backend.app.services import sleep as svc
    as_of = date(2026, 6, 2)
    _insert_sleep(seeded_conn, "amy", night_of=as_of - timedelta(days=20), duration_min=450)
    _insert_sleep(seeded_conn, "amy", night_of=as_of - timedelta(days=35), duration_min=999)

    resp = svc.get_user_monthly(seeded_conn, "amy", as_of)

    assert resp.month_start == as_of - timedelta(days=29)
    assert resp.month_end == as_of
    assert len(resp.daily_breakdown) == 30  # sleep monthly zero-fills the span
    assert resp.monthly_total == 450
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_sleep_service.py -q -k "rolling"`
Expected: FAIL (still ISO-week / calendar-month).

- [ ] **Step 3: Implement — same edits as steps, in `sleep.py`**

In `backend/app/services/sleep.py`:
(a) Delete `_month_bounds` (~lines 90–99) and `_iso_week_bounds` (~85–87); add `from backend.app.services.windows import rolling_bounds`.
(b) `get_global_weekly(conn, as_of)`: `start, end = rolling_bounds(as_of, 7)`.
(c) `get_global_summary(conn, as_of)`: `today_leader = _top_leader(conn, as_of, as_of)`; `week_start, week_end = rolling_bounds(as_of, 7)`; `this_week_leader = _top_leader(conn, week_start, week_end)`.
(d) `get_user_weekly(conn, username, as_of)`: `start, end = rolling_bounds(as_of, 7)`.
(e) `get_user_monthly(conn, username, as_of)`: `start, end = rolling_bounds(as_of, 30)` (keep the existing `span = (end - start).days + 1` zero-fill loop — it will produce 30 entries).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_sleep_service.py -q`
Expected: rolling tests PASS; fix any existing sleep service tests asserting old bounds in Step 5.

- [ ] **Step 5: Update existing sleep service tests + commit**

Update sleep service tests that called the old signatures / asserted ISO-week / calendar-month bounds (same transformation as Task 2 Step 5).

Run: `cd backend && python -m pytest tests/test_sleep_service.py -q`
Expected: all PASS.

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add backend/app/services/sleep.py backend/tests/test_sleep_service.py
git commit -m "feat(backend): sleep weekly/monthly/summary use rolling windows via as_of

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Routes (steps + sleep) → `?as_of=` param

**Files:**
- Modify: `backend/app/routes/steps.py`, `backend/app/routes/sleep.py`
- Test: `backend/tests/test_steps_routes.py`, `backend/tests/test_sleep_routes.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_steps_routes.py` (use the existing TestClient + seed pattern in that file):
```python
def test_user_weekly_route_accepts_as_of_and_returns_rolling_bounds(client_with_amy):
    resp = client_with_amy.get("/api/steps/users/amy/weekly?as_of=2026-06-02")
    assert resp.status_code == 200
    body = resp.json()
    assert body["week_start"] == "2026-05-27"
    assert body["week_end"] == "2026-06-02"
    assert len(body["daily_breakdown"]) == 7


def test_user_monthly_route_accepts_as_of(client_with_amy):
    resp = client_with_amy.get("/api/steps/users/amy/monthly?as_of=2026-06-02")
    assert resp.status_code == 200
    body = resp.json()
    assert body["month_start"] == "2026-05-04"
    assert body["month_end"] == "2026-06-02"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_steps_routes.py -q -k "as_of"`
Expected: FAIL — `?as_of` is ignored (still `?week_start`/`?month`); monthly returns calendar-month bounds.

- [ ] **Step 3: Implement route changes**

In `backend/app/routes/steps.py` (and make the identical changes in `backend/app/routes/sleep.py`):

(a) Delete the now-unused `_iso_monday` helper.

(b) `global_weekly`:
```python
@router.get("/weekly", response_model=GlobalWeeklyResponse)
def global_weekly(
    as_of: Optional[date] = Query(default=None),
) -> GlobalWeeklyResponse:
    anchor = as_of or _today()
    with db.get_engine().connect() as conn:
        return svc.get_global_weekly(conn, anchor)
```

(c) `global_summary`:
```python
@router.get("/summary", response_model=GlobalSummaryResponse)
def global_summary() -> GlobalSummaryResponse:
    with db.get_engine().connect() as conn:
        return svc.get_global_summary(conn, _today())
```

(d) `user_weekly`:
```python
@router.get("/users/{username}/weekly", response_model=UserWeeklyResponse)
def user_weekly(
    username: str,
    as_of: Optional[date] = Query(default=None),
) -> UserWeeklyResponse:
    anchor = as_of or _today()
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_weekly(conn, username, anchor)
    except svc.UserNotFound as e:
        raise _user_not_found(e.username) from e
```

(e) `user_monthly` — replace the `month` param entirely:
```python
@router.get("/users/{username}/monthly", response_model=UserMonthlyResponse)
def user_monthly(
    username: str,
    as_of: Optional[date] = Query(default=None),
) -> UserMonthlyResponse:
    """One user's stats for the rolling last 30 days ending `as_of`
    (CT today by default)."""
    anchor = as_of or _today()
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_monthly(conn, username, anchor)
    except svc.UserNotFound as e:
        raise _user_not_found(e.username) from e
```

The `sleep.py` route file is identical in structure (same handler bodies, same `_today`); apply (a)–(e) there too. Daily + summary-less endpoints stay as-is.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_steps_routes.py tests/test_sleep_routes.py -q -k "as_of"`
Expected: PASS.

- [ ] **Step 5: Update existing route tests + full backend run + commit**

Replace any `?week_start=YYYY-MM-DD` / `?month=YYYY-MM` query strings in `test_steps_routes.py` / `test_sleep_routes.py` with `?as_of=YYYY-MM-DD`, and update bound assertions to rolling (`as_of-6..as_of`, `as_of-29..as_of`). Remove any test of `_iso_monday`.

Run: `cd backend && python -m pytest -q`
Expected: entire backend suite PASS.

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add backend/app/routes/steps.py backend/app/routes/sleep.py backend/tests/test_steps_routes.py backend/tests/test_sleep_routes.py
git commit -m "feat(backend): weekly/monthly/summary routes take ?as_of, rolling windows

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Frontend `lastNightDate()` helper

**Files:**
- Modify: `frontend/src/lib/dates.ts`
- Test: `frontend/src/lib/__tests__/dates.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/lib/__tests__/dates.test.ts` (add `lastNightDate` to the existing `@/lib/dates` import):
```ts
describe('lastNightDate', () => {
  it('is the CT day before today (the night_of you woke from this morning)', () => {
    const now = new Date('2026-06-02T18:00:00Z'); // ~1pm CT, 2026-06-02
    expect(lastNightDate(now)).toBe('2026-06-01');
  });

  it('matches YYYY-MM-DD shape', () => {
    expect(lastNightDate()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/lib/__tests__/dates.test.ts`
Expected: FAIL — `lastNightDate` not exported.

- [ ] **Step 3: Implement**

In `frontend/src/lib/dates.ts`, add after `currentDate()`:
```ts
/**
 * The night_of of the night you woke from this morning — i.e. the CT
 * calendar day BEFORE today. Sleep's `night_of` is wake-date minus one,
 * so "last night" on the profile is today - 1. Used by the sleep
 * "Last night" card (distinct from steps' "today").
 */
export function lastNightDate(now: Date = new Date()): string {
  const todayCt = ISO_DATE_PARTS.format(now); // YYYY-MM-DD in CT
  const [y, m, d] = todayCt.split('-').map(Number);
  const prev = new Date(Date.UTC(y, m - 1, d - 1));
  return prev.toISOString().slice(0, 10);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/lib/__tests__/dates.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add frontend/src/lib/dates.ts frontend/src/lib/__tests__/dates.test.ts
git commit -m "feat(dates): add lastNightDate (today-1) for the sleep Last-night card

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Frontend fetchers + query builders

**Files:**
- Modify: `frontend/src/api/steps.ts`, `frontend/src/api/sleep.ts`
- Modify: `frontend/src/api/userSummaryQueries.ts`
- Test: `frontend/src/api/__tests__/userSummaryQueries.test.ts`

- [ ] **Step 1: Write the failing test**

Replace the key-shape assertions in `frontend/src/api/__tests__/userSummaryQueries.test.ts` so the weekly/monthly keys include `today` and the sleep daily key uses `lastNight`. Add:
```ts
import { userSummaryQueries } from '@/api/userSummaryQueries';

it('weekly/monthly keys are date-stamped with the as-of day, sleep daily uses last night', () => {
  const keys = userSummaryQueries('alice', '2026-06-02', '2026-06-01').map((q) => q.queryKey);
  expect(keys).toEqual([
    ['steps', 'users', 'alice', 'summary'],
    ['steps', 'users', 'alice', 'daily', '2026-06-02'],
    ['steps', 'users', 'alice', 'weekly', '2026-06-02'],
    ['steps', 'users', 'alice', 'monthly', '2026-06-02'],
    ['sleep', 'users', 'alice', 'summary'],
    ['sleep', 'users', 'alice', 'daily', '2026-06-01'],
    ['sleep', 'users', 'alice', 'weekly', '2026-06-02'],
    ['sleep', 'users', 'alice', 'monthly', '2026-06-02'],
  ]);
});
```
(Remove/replace the old test that asserted `weekly` keys without a date and `monthly` keyed on a `YYYY-MM` month.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/api/__tests__/userSummaryQueries.test.ts`
Expected: FAIL — current weekly keys have no date; monthly keyed on month; `userSummaryQueries` takes `(u, today, month)`.

- [ ] **Step 3: Implement — fetchers**

In `frontend/src/api/steps.ts` AND `frontend/src/api/sleep.ts`, change the three fetchers to send `?as_of=`:
```ts
export function getGlobalWeekly(asOf?: string): Promise<GlobalWeeklyResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return apiFetch<GlobalWeeklyResponse>(`/steps/weekly${qs}`);
}

export function getUserWeekly(username: string, asOf?: string): Promise<UserWeeklyResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return apiFetch<UserWeeklyResponse>(`/steps/users/${encodeURIComponent(username)}/weekly${qs}`);
}

export function getUserMonthly(username: string, asOf?: string): Promise<UserMonthlyResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return apiFetch<UserMonthlyResponse>(`/steps/users/${encodeURIComponent(username)}/monthly${qs}`);
}
```
(In `sleep.ts` the path prefix is `/sleep/...`; otherwise identical. `getGlobalWeekly` only exists in steps.ts.)

- [ ] **Step 4: Implement — query builders**

In `frontend/src/api/userSummaryQueries.ts`:

(a) The weekly builders take `asOf` and date-stamp the key + pass it to the fetcher:
```ts
export const stepsWeeklyQuery = (u: string, asOf: string) => ({
  queryKey: ['steps', 'users', u, 'weekly', asOf] as const,
  queryFn: () => getStepsWeekly(u, asOf),
  staleTime: STALE,
  retry: false as const,
});

export const sleepWeeklyQuery = (u: string, asOf: string) => ({
  queryKey: ['sleep', 'users', u, 'weekly', asOf] as const,
  queryFn: () => getSleepWeekly(u, asOf),
  staleTime: STALE,
  retry: false as const,
});
```

(b) The monthly builders take `asOf` instead of `month`:
```ts
export const stepsMonthlyQuery = (u: string, asOf: string) => ({
  queryKey: ['steps', 'users', u, 'monthly', asOf] as const,
  queryFn: () => getStepsMonthly(u, asOf),
  staleTime: STALE,
  retry: false as const,
});

export const sleepMonthlyQuery = (u: string, asOf: string) => ({
  queryKey: ['sleep', 'users', u, 'monthly', asOf] as const,
  queryFn: () => getSleepMonthly(u, asOf),
  staleTime: STALE,
  retry: false as const,
});
```

(c) `userSummaryQueries` — signature `(u, today, lastNight)`; steps daily uses `today`, sleep daily uses `lastNight`, weekly/monthly use `today`:
```ts
export function userSummaryQueries(
  u: string,
  today: string,
  lastNight: string,
): FetchQueryOptions[] {
  return [
    stepsSummaryQuery(u),
    stepsDailyQuery(u, today),
    stepsWeeklyQuery(u, today),
    stepsMonthlyQuery(u, today),
    sleepSummaryQuery(u),
    sleepDailyQuery(u, lastNight),
    sleepWeeklyQuery(u, today),
    sleepMonthlyQuery(u, today),
  ];
}
```
(`stepsDailyQuery`, `sleepDailyQuery`, `stepsSummaryQuery`, `sleepSummaryQuery` are unchanged — daily already takes a date param.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/api/__tests__/userSummaryQueries.test.ts`
Expected: PASS. (TypeScript callers in Profile/Users break until Task 7 — that's expected; typecheck runs in Task 7 Step 5.)

- [ ] **Step 6: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add frontend/src/api/steps.ts frontend/src/api/sleep.ts frontend/src/api/userSummaryQueries.ts frontend/src/api/__tests__/userSummaryQueries.test.ts
git commit -m "feat(api): weekly/monthly queries take as_of (date-stamped keys); sleep daily = last night

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Profile + Users prefetch + Leaderboard (call sites + labels)

**Files:**
- Modify: `frontend/src/pages/Profile.tsx`
- Modify: `frontend/src/pages/Users.tsx`
- Modify: `frontend/src/pages/Leaderboard.tsx`
- Test: `frontend/src/__tests__/Leaderboard.test.tsx`, `frontend/src/__tests__/Users.test.tsx`

- [ ] **Step 1: Write the failing test**

In `frontend/src/__tests__/Leaderboard.test.tsx`, assert the renamed tab/heading. Add (or adapt an existing render test):
```ts
it('labels the weekly tab "Last 7 days"', async () => {
  // existing fetch mock for getGlobalDaily/getGlobalWeekly
  renderLeaderboard();
  expect(await screen.findByText('Last 7 days')).toBeInTheDocument();
  expect(screen.queryByText('This Week')).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/__tests__/Leaderboard.test.tsx`
Expected: FAIL — tab still labeled "This Week".

- [ ] **Step 3: Implement — Profile.tsx**

(a) `SummaryPanel` (lines ~332–344): compute `lastNight`, drop `month`, pass `today` to weekly/monthly and `lastNight` to sleep daily:
```tsx
  const today = currentDate();
  const lastNight = lastNightDate();

  const summary = useQuery({ ...stepsSummaryQuery(username), enabled: !!username });
  const daily = useQuery({ ...stepsDailyQuery(username, today), enabled: !!username });
  const weekly = useQuery({ ...stepsWeeklyQuery(username, today), enabled: !!username });
  const monthly = useQuery({ ...stepsMonthlyQuery(username, today), enabled: !!username });

  const sleepSummary = useQuery({ ...sleepSummaryQuery(username), enabled: !!username });
  const sleepDaily = useQuery({ ...sleepDailyQuery(username, lastNight), enabled: !!username });
  const sleepWeekly = useQuery({ ...sleepWeeklyQuery(username, today), enabled: !!username });
  const sleepMonthly = useQuery({ ...sleepMonthlyQuery(username, today), enabled: !!username });
```
(b) Update the import line `import { currentDate, currentMonthYYYYMM } from '@/lib/dates';` → `import { currentDate, lastNightDate } from '@/lib/dates';` (drop `currentMonthYYYYMM` if now unused in this file — verify with a grep; if still used elsewhere in the file, keep it).
(c) Relabel cards: in `ThisWeekCard` and `SleepThisWeekCard`, `>This week<` → `>Last 7 days<`. In `ThisMonthCard` and `SleepThisMonthCard`, `>This month<` → `>Last 30 days<`, and the empty strings `No activity this month yet.` → `No activity in the last 30 days yet.` and `No sleep this month yet.` → `No sleep in the last 30 days yet.`.

- [ ] **Step 4: Implement — Users.tsx prefetch + Leaderboard.tsx**

(a) `frontend/src/pages/Users.tsx`: the hover prefetch calls `userSummaryQueries(profile.username, today, month)`. Change to pass `lastNight`:
```tsx
import { currentDate, lastNightDate } from '@/lib/dates';
// ...inside the prefetch handler:
    const today = currentDate();
    const lastNight = lastNightDate();
    for (const q of userSummaryQueries(profile.username, today, lastNight)) {
      queryClient.prefetchQuery(q);
    }
```
(remove the `currentMonthYYYYMM` import/use in Users.tsx).

(b) `frontend/src/pages/Leaderboard.tsx`:
- `TABS`: `{ key: 'week', label: 'This Week' }` → `{ key: 'week', label: 'Last 7 days' }`.
- `WeeklyPanel`: date-stamp the key and pass today:
```tsx
function WeeklyPanel() {
  const today = currentDate();
  const query = useQuery({
    queryKey: ['steps', 'weekly', today],
    queryFn: () => getGlobalWeekly(today),
    staleTime: 30_000,
  });
```
(`currentDate` is already imported in Leaderboard.tsx.)

- [ ] **Step 5: Run the full check (frontend + backend) + verify**

Run:
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows/frontend
npm test -- --run && npm run typecheck && npx eslint src/pages/Profile.tsx src/pages/Users.tsx src/pages/Leaderboard.tsx src/api/userSummaryQueries.ts src/api/steps.ts src/api/sleep.ts src/lib/dates.ts
cd ../backend && python -m pytest -q
```
Expected: all frontend tests pass, typecheck clean, eslint exits 0 for the changed files; full backend suite passes.

- [ ] **Step 6: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add frontend/src/pages/Profile.tsx frontend/src/pages/Users.tsx frontend/src/pages/Leaderboard.tsx frontend/src/__tests__/Leaderboard.test.tsx frontend/src/__tests__/Users.test.tsx
git commit -m "feat(feed): rolling-window call sites + 'Last 7/30 days' labels + last-night card

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:**
  - Shared rolling helper → Task 1. ✓
  - Steps service rolling + as_of → Task 2. ✓ Sleep service → Task 3. ✓
  - Routes `?as_of` (steps + sleep, per-user + global + summary) → Task 4. ✓
  - `lastNightDate` off-by-one helper → Task 5; applied at sleep daily call sites → Tasks 6 (builder array) + 7 (Profile, Users prefetch). ✓
  - Frontend weekly/monthly keys date-stamped; monthly drops `month` → Task 6. ✓
  - Labels "Last 7 days"/"Last 30 days" (profile cards + leaderboard tab) → Task 7. ✓
  - Query-key parity (prefetch vs Profile) → Task 6 `userSummaryQueries(u, today, lastNight)` + Task 7 Profile/Users both pass `today`+`lastNight`. ✓
  - Tests at every layer (windows, services, routes, dates, builders, Leaderboard) → Tasks 1–7. ✓
- **Placeholder scan:** none — every code step has concrete before→after or full code; existing-test updates specify the exact mechanical transformation (param/bounds) with example assertions.
- **Type consistency:** `rolling_bounds(end, days)` signature consistent (Tasks 1–4). Service functions all take `as_of: date` (Tasks 2–4). Builders all take `asOf: string`; `userSummaryQueries(u, today, lastNight)` matches its callers in Profile.tsx + Users.tsx (Tasks 6–7). Fetchers `getUser{Weekly,Monthly}(username, asOf?)` and `getGlobalWeekly(asOf?)` match builder call sites (Task 6). `lastNightDate(now?)` matches its test + call sites.
