# Sleep in the feed + profile pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface sleep activity in the global feed (one post per logged night) and on profile pages (a sleep stats section alongside steps).

**Architecture:** The sleep backend (`sleep` table + `/api/sleep` endpoints) already shipped in PR #40. This plan adds (1) a post-on-write in the sleep route so sleep appears in the `posts`-driven feed, and (2) a frontend sleep API wrapper + a sleep stats section on the profile, reusing existing components. The feed is post-table-driven, so the backend change is what makes sleep visible there.

**Tech Stack:** FastAPI + SQLAlchemy `text()` (backend), pytest w/ in-memory SQLite; React + TypeScript + React Query + Tailwind (frontend), vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-05-29-sleep-feed-and-profile-design.md`

**Working directory:** the worktree at `.claude/worktrees/sleep-feed-and-pages` (branch `worktree-sleep-feed-and-pages`). Backend commands run from `backend/`, frontend from `frontend/`.

---

## Task 1: Backend — a sleep write also creates a `type='sleep'` feed post

**Files:**
- Modify: `backend/app/services/sleep.py` (add `import json`, a body formatter, and `create_sleep_post`)
- Modify: `backend/app/routes/sleep.py` (call `create_sleep_post` inside the existing transaction)
- Test: `backend/tests/test_sleep_write.py` (add `posts` table to the fixture + two new tests)

- [ ] **Step 1: Add the `posts` table to the sleep-write test fixture**

In `backend/tests/test_sleep_write.py`, inside `_engine_with_users()`, after the `CREATE TABLE sleep (...)` block and before the `INSERT INTO profiles` block, add:

```python
        conn.execute(
            text(
                "CREATE TABLE posts ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "username text not null, "
                "type text not null, "
                "timestamp text not null, "
                "details text, "
                "body text)"
            )
        )
```

(The route will now insert a post in the same transaction as the sleep row; without this table the existing write tests would fail.)

- [ ] **Step 2: Add a `_count_posts` helper + the two new tests**

In `backend/tests/test_sleep_write.py`, after the existing `_count_sleep` helper add:

```python
import json


def _count_posts(engine) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(text("SELECT count(*) FROM posts")).scalar() or 0
        )
```

Then, at the end of the file, add:

```python
def test_post_sleep_creates_feed_post(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    resp = TestClient(main.app).post(
        "/api/sleep",
        json={
            "bedtime": "2026-05-28T05:00:00",
            "wake_time": "2026-05-28T12:32:00",
            "duration_min": 452,
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )
    assert resp.status_code == 201, resp.text

    with engine.connect() as conn:
        post = (
            conn.execute(
                text(
                    "SELECT username, type, timestamp, details, body "
                    "FROM posts"
                )
            )
            .mappings()
            .one()
        )
        sleep_night = conn.execute(
            text("SELECT night_of FROM sleep")
        ).scalar()

    assert post["username"] == "alice"
    assert post["type"] == "sleep"
    assert post["body"] == "slept 7h 32m"
    details = json.loads(post["details"])
    assert details["duration_min"] == 452
    assert details["night_of"] == sleep_night
    # Post timestamp anchors to wake_time so morning syncs land on top.
    assert "2026-05-28T12:32:00" in post["timestamp"]


def test_duplicate_night_creates_no_second_post(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)
    body = {
        "bedtime": "2026-05-28T05:00:00",
        "wake_time": "2026-05-28T12:32:00",
        "duration_min": 452,
    }
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    first = client.post("/api/sleep", json=body, headers=headers)
    assert first.status_code == 201
    second = client.post("/api/sleep", json=body, headers=headers)
    assert second.status_code == 409

    # The duplicate night rolled back — exactly one post, one sleep row.
    assert _count_posts(engine) == 1
    assert _count_sleep(engine) == 1
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_sleep_write.py -q`
Expected: the two new tests FAIL (no `posts` row created — `create_sleep_post` doesn't exist yet). The pre-existing write tests should still PASS (the fixture now has a `posts` table they don't use).

- [ ] **Step 4: Implement `create_sleep_post` in the service**

In `backend/app/services/sleep.py`, add `import json` to the stdlib imports near the top (after `from collections import defaultdict`):

```python
import json
```

Then, in the "Write" section of the file (just below `_night_of_for` / above or below `create_sleep`), add:

```python
def _format_sleep_body(duration_min: int) -> str:
    """Pre-rendered feed text, e.g. 'slept 7h 32m'. Mirrors how
    steps_milestone posts store a ready-to-display body."""
    hours, minutes = divmod(duration_min, 60)
    return f"slept {hours}h {minutes}m"


def create_sleep_post(
    conn: Connection,
    user_id: int,
    duration_min: int,
    night_of: date,
    wake_time: datetime,
) -> None:
    """Insert one feed post for a logged night. Called from the sleep
    route in the SAME transaction as create_sleep, so a duplicate-night
    rollback (409) takes the post with it. `type='sleep'` is already an
    allowed post type (migration 0007 CHECK). The username is looked up
    server-side — never trusted from the request body."""
    username_row = (
        conn.execute(
            text("SELECT username FROM profiles WHERE id = :uid"),
            {"uid": user_id},
        )
        .mappings()
        .first()
    )
    if username_row is None:
        return
    details_str = json.dumps(
        {"duration_min": duration_min, "night_of": night_of.isoformat()}
    )
    conn.execute(
        text(
            "INSERT INTO posts "
            "(user_id, username, type, timestamp, details, body) "
            "VALUES (:uid, :u, 'sleep', :ts, :details, :body)"
        ),
        {
            "uid": user_id,
            "u": username_row["username"],
            "ts": wake_time,
            "details": details_str,
            "body": _format_sleep_body(duration_min),
        },
    )
```

- [ ] **Step 5: Call it from the route**

In `backend/app/routes/sleep.py`, the `create_sleep` route currently does:

```python
        with db.get_engine().begin() as conn:
            return svc.create_sleep(
                conn,
                user_id=user_id,
                bedtime=req.bedtime,
                wake_time=req.wake_time,
                duration_min=req.duration_min,
                rem_minutes=req.rem_minutes,
                core_minutes=req.core_minutes,
                deep_minutes=req.deep_minutes,
                awake_minutes=req.awake_minutes,
            )
```

Replace that block with:

```python
        with db.get_engine().begin() as conn:
            result = svc.create_sleep(
                conn,
                user_id=user_id,
                bedtime=req.bedtime,
                wake_time=req.wake_time,
                duration_min=req.duration_min,
                rem_minutes=req.rem_minutes,
                core_minutes=req.core_minutes,
                deep_minutes=req.deep_minutes,
                awake_minutes=req.awake_minutes,
            )
            svc.create_sleep_post(
                conn,
                user_id=user_id,
                duration_min=result.duration_min,
                night_of=result.night_of,
                wake_time=result.wake_time,
            )
            return result
```

(`create_sleep` raises `IntegrityError` on a duplicate night BEFORE `create_sleep_post` runs, and the route's existing `except IntegrityError` maps it to 409 — so the post is never inserted for a duplicate.)

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && python -m pytest tests/ -q`
Expected: PASS — all previously-passing tests (105) plus the 2 new ones.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/sleep.py backend/app/routes/sleep.py backend/tests/test_sleep_write.py
git commit -m "feat(backend): sleep write posts to the feed (type='sleep')"
```

---

## Task 2: Frontend — `formatDuration` helper

**Files:**
- Modify: `frontend/src/lib/dates.ts` (add `formatDuration`)
- Test: `frontend/src/lib/__tests__/dates.test.ts` (NEW)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/__tests__/dates.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { formatDuration } from '@/lib/dates';

describe('formatDuration', () => {
  it('formats minutes as "Xh Ym"', () => {
    expect(formatDuration(452)).toBe('7h 32m');
  });

  it('handles whole hours', () => {
    expect(formatDuration(480)).toBe('8h 0m');
  });

  it('handles zero', () => {
    expect(formatDuration(0)).toBe('0h 0m');
  });

  it('handles sub-hour durations', () => {
    expect(formatDuration(45)).toBe('0h 45m');
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npm test -- --run src/lib/__tests__/dates.test.ts`
Expected: FAIL — `formatDuration` is not exported.

- [ ] **Step 3: Implement**

In `frontend/src/lib/dates.ts`, add at the end of the file:

```ts
/** Render a minute count as "7h 32m". Used for sleep durations. */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd frontend && npm test -- --run src/lib/__tests__/dates.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/dates.ts frontend/src/lib/__tests__/dates.test.ts
git commit -m "feat(frontend): formatDuration helper for sleep durations"
```

---

## Task 3: Frontend — `api/sleep.ts` wrapper

**Files:**
- Create: `frontend/src/api/sleep.ts`

(No dedicated test — this mirrors `api/steps.ts`, which has none; it's exercised through the Profile test in Task 6.)

- [ ] **Step 1: Create the wrapper**

Create `frontend/src/api/sleep.ts`:

```ts
import { apiFetch } from './client';

export interface DailyTotal {
  date: string;
  total: number; // minutes
}

export interface SleepPostDetail {
  night_of: string;
  bedtime: string;
  wake_time: string;
  duration_min: number;
  rem_minutes: number | null;
  core_minutes: number | null;
  deep_minutes: number | null;
  awake_minutes: number | null;
}

export interface UserDailyResponse {
  username: string;
  date: string;
  total: number; // duration_min for that night
  rank_today: number | null;
  post: SleepPostDetail | null;
}

export interface UserWeeklyResponse {
  username: string;
  week_start: string;
  week_end: string;
  weekly_total: number;
  rank_this_week: number | null;
  daily_breakdown: DailyTotal[];
}

export interface UserMonthlyResponse {
  username: string;
  month_start: string;
  month_end: string;
  monthly_total: number;
  rank_this_month: number | null;
  daily_breakdown: DailyTotal[];
}

export interface UserBestNight {
  date: string;
  total: number;
}

export interface UserSummaryResponse {
  username: string;
  join_date: string;
  total_minutes_all_time: number;
  best_night: UserBestNight | null;
  rank_all_time: number | null;
  nights_logged: number;
}

export function getUserDaily(
  username: string,
  date?: string,
): Promise<UserDailyResponse> {
  const qs = date ? `?date=${encodeURIComponent(date)}` : '';
  return apiFetch<UserDailyResponse>(
    `/sleep/users/${encodeURIComponent(username)}/daily${qs}`,
  );
}

export function getUserWeekly(
  username: string,
  weekStart?: string,
): Promise<UserWeeklyResponse> {
  const qs = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : '';
  return apiFetch<UserWeeklyResponse>(
    `/sleep/users/${encodeURIComponent(username)}/weekly${qs}`,
  );
}

export function getUserMonthly(
  username: string,
  month?: string,
): Promise<UserMonthlyResponse> {
  const qs = month ? `?month=${encodeURIComponent(month)}` : '';
  return apiFetch<UserMonthlyResponse>(
    `/sleep/users/${encodeURIComponent(username)}/monthly${qs}`,
  );
}

export function getUserSummary(username: string): Promise<UserSummaryResponse> {
  return apiFetch<UserSummaryResponse>(
    `/sleep/users/${encodeURIComponent(username)}/summary`,
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/sleep.ts
git commit -m "feat(frontend): /api/sleep client wrapper"
```

---

## Task 4: Frontend — `SleepPost` feed component + dispatch

**Files:**
- Create: `frontend/src/components/feed/SleepPost.tsx`
- Create: `frontend/src/components/feed/__tests__/SleepPost.test.tsx`
- Modify: `frontend/src/pages/Feed.tsx` (dispatch)
- Modify: `frontend/src/pages/Profile.tsx` (FeedPanel dispatch)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/feed/__tests__/SleepPost.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SleepPost from '@/components/feed/SleepPost';
import type { FeedPost } from '@/api/posts';

const post: FeedPost = {
  id: 1,
  user_id: 1,
  username: 'alice',
  type: 'sleep',
  timestamp: '2026-05-28T12:32:00Z',
  details: { duration_min: 452, night_of: '2026-05-27' },
  body: 'slept 7h 32m',
};

describe('SleepPost', () => {
  it('renders the username and body', () => {
    render(
      <MemoryRouter>
        <SleepPost post={post} />
      </MemoryRouter>,
    );
    expect(screen.getByText('@alice')).toBeInTheDocument();
    expect(screen.getByText('slept 7h 32m')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npm test -- --run src/components/feed/__tests__/SleepPost.test.tsx`
Expected: FAIL — `SleepPost` module not found.

- [ ] **Step 3: Create the component**

Create `frontend/src/components/feed/SleepPost.tsx` (mirrors `MilestonePost.tsx`):

```tsx
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';

export default function SleepPost({ post }: { post: FeedPost }) {
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
          🌙 {post.body ?? 'logged sleep'}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}
```

- [ ] **Step 4: Run the component test to verify it passes**

Run: `cd frontend && npm test -- --run src/components/feed/__tests__/SleepPost.test.tsx`
Expected: PASS.

- [ ] **Step 5: Wire dispatch into the global feed**

In `frontend/src/pages/Feed.tsx`, add the import near the other feed-component imports:

```tsx
import SleepPost from '@/components/feed/SleepPost';
```

Then in the `.map((post) => {...})` block, add this branch BEFORE the final `return <GenericPost ... />`:

```tsx
            if (post.type === 'sleep') {
              return <SleepPost key={post.id} post={post} />;
            }
```

- [ ] **Step 6: Wire dispatch into the per-user feed**

In `frontend/src/pages/Profile.tsx`, add to the feed-component imports:

```tsx
import SleepPost from '@/components/feed/SleepPost';
```

In `FeedPanel`'s `.map((post: FeedPost) => {...})`, add before the final `return <GenericPost ... />;`:

```tsx
        if (post.type === 'sleep') return <SleepPost key={post.id} post={post} />;
```

- [ ] **Step 7: Run the full frontend suite + typecheck**

Run: `cd frontend && npx tsc --noEmit && npm test -- --run`
Expected: PASS (all tests, including the new SleepPost test).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/feed/SleepPost.tsx frontend/src/components/feed/__tests__/SleepPost.test.tsx frontend/src/pages/Feed.tsx frontend/src/pages/Profile.tsx
git commit -m "feat(frontend): SleepPost feed component + dispatch"
```

---

## Task 5: Frontend — `DailyBars` value formatter prop

`DailyBars` hardcodes `formatNumber` and the word "steps" in its tooltip/aria-label. Add optional props so sleep can render `7h 32m` without breaking steps.

**Files:**
- Modify: `frontend/src/components/ui/DailyBars.tsx`

- [ ] **Step 1: Add the optional props**

In `frontend/src/components/ui/DailyBars.tsx`, replace the `DailyBarsProps` interface and the component body with:

```tsx
interface DailyBarsProps {
  days: DailyTotal[];
  /** Number of grid columns; defaults to days.length. Use 7 for a week,
   *  28-31 for a month. */
  cols?: number;
  /** Formats a day's value for the tooltip/aria-label. Defaults to a
   *  plain number (steps). Sleep passes formatDuration. */
  formatValue?: (n: number) => string;
  /** Unit suffix appended to the aria-label, e.g. "steps". Pass "" to
   *  omit (sleep's formatValue already reads as "7h 32m"). */
  unit?: string;
}

export default function DailyBars({
  days,
  cols,
  formatValue = formatNumber,
  unit = 'steps',
}: DailyBarsProps) {
  const n = cols ?? days.length;
  const max = Math.max(...days.map((d) => d.total), 1);
  return (
    <div
      className="grid gap-2 h-28 items-end"
      style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}
    >
      {days.map((d) => {
        const heightPct = (d.total / max) * 100;
        const valueLabel = unit
          ? `${formatValue(d.total)} ${unit}`
          : formatValue(d.total);
        return (
          <div
            key={d.date}
            className="flex flex-col items-center gap-1.5 h-full"
            title={`${d.date}: ${formatValue(d.total)}`}
          >
            <div className="flex-1 w-full flex items-end">
              <div
                className="w-full bg-primary/70 rounded-t"
                style={{ height: `${Math.max(heightPct, 2)}%` }}
                aria-label={`${d.date}: ${valueLabel}`}
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

(Steps callers pass nothing → identical behavior: title `452`, aria-label `…: 452 steps`.)

- [ ] **Step 2: Run frontend tests + typecheck to confirm no regression**

Run: `cd frontend && npx tsc --noEmit && npm test -- --run`
Expected: PASS — existing steps DailyBars rendering unchanged.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/DailyBars.tsx
git commit -m "feat(frontend): DailyBars accepts a value formatter + unit"
```

---

## Task 6: Frontend — Profile SLEEP section

Add a "Sleep" section beneath the existing steps cards in the Profile `SummaryPanel`, with a "Steps" heading over the existing cards.

**Files:**
- Modify: `frontend/src/pages/Profile.tsx`
- Test: `frontend/src/__tests__/Profile.test.tsx`

> **Why these test edits are needed (read first):** `routedMock` matches handler keys with `String.includes()`. The existing `summaryMocks()` uses loose keys (`/summary`, `/daily`, `/weekly`, `/monthly`) that ALSO match the new `/sleep/users/.../summary` URLs. Once `SummaryPanel` fires sleep queries, those loose keys would feed *steps* payloads to the sleep cards, and `SleepStatStrip`'s `formatNumber(data.nights_logged)` would throw on `undefined`. So we must add real sleep handlers, keyed by full `/sleep/...` paths placed BEFORE the loose keys (first match wins). Two existing tests also need touch-ups (duplicate headings; dash counts).

- [ ] **Step 1a: Add sleep payload builders**

In `frontend/src/__tests__/Profile.test.tsx`, near the other `alice*` builders (after `aliceMonthly`), add:

```tsx
function aliceSleepSummary() {
  return ok({
    username: 'alice',
    join_date: '2026-05-01T00:00:00Z',
    total_minutes_all_time: 8520,
    best_night: { date: '2026-05-20', total: 512 },
    rank_all_time: 2,
    nights_logged: 12,
  });
}

function aliceSleepDaily() {
  return ok({
    username: 'alice',
    date: '2026-05-23',
    total: 452,
    rank_today: 1,
    post: {
      night_of: '2026-05-22',
      bedtime: '2026-05-22T05:00:00',
      wake_time: '2026-05-23T12:32:00',
      duration_min: 452,
      rem_minutes: null,
      core_minutes: null,
      deep_minutes: null,
      awake_minutes: null,
    },
  });
}

function aliceSleepWeekly() {
  return ok({
    username: 'alice',
    week_start: '2026-05-18',
    week_end: '2026-05-24',
    weekly_total: 2710,
    rank_this_week: 1,
    daily_breakdown: [
      { date: '2026-05-18', total: 452 },
      { date: '2026-05-19', total: 400 },
      { date: '2026-05-20', total: 512 },
      { date: '2026-05-21', total: 0 },
      { date: '2026-05-22', total: 446 },
      { date: '2026-05-23', total: 450 },
      { date: '2026-05-24', total: 450 },
    ],
  });
}

function aliceSleepMonthly() {
  return ok({
    username: 'alice',
    month_start: '2026-05-01',
    month_end: '2026-05-31',
    monthly_total: 8520,
    rank_this_month: 2,
    daily_breakdown: [{ date: '2026-05-20', total: 512 }],
  });
}
```

- [ ] **Step 1b: Add sleep handlers to `summaryMocks()` (sleep keys FIRST)**

Replace the existing `summaryMocks()` body with:

```tsx
function summaryMocks() {
  // Pattern order matters because routedMock uses includes() and
  // returns on first match. Full /sleep/... paths come first so they
  // aren't shadowed by the loose /summary, /daily, ... steps keys.
  return {
    '/sleep/users/alice/summary': aliceSleepSummary,
    '/sleep/users/alice/daily': aliceSleepDaily,
    '/sleep/users/alice/weekly': aliceSleepWeekly,
    '/sleep/users/alice/monthly': aliceSleepMonthly,
    '/summary': aliceSummary,
    '/daily': aliceDaily,
    '/weekly': aliceWeekly,
    '/monthly': aliceMonthly,
  };
}
```

- [ ] **Step 1c: Fix the duplicate-heading assertions in the "stat strip / today / week / month" test**

The steps and sleep sections both render "This week" and "This month" headings. In the test titled `'renders header, stat strip, today, week, and month cards'`, change the two colliding single-match queries:

```tsx
      // Today / Week / Month headings
      expect(await screen.findByText('Today')).toBeInTheDocument();
      expect(await screen.findByText('This week')).toBeInTheDocument();
      expect(await screen.findByText('This month')).toBeInTheDocument();
```

to:

```tsx
      // 'Today' is steps-only (sleep card says 'Last night'); the
      // week/month headings now appear in both the Steps and Sleep
      // sections.
      expect(await screen.findByText('Today')).toBeInTheDocument();
      expect(await screen.findAllByText('This week')).toHaveLength(2);
      expect(await screen.findAllByText('This month')).toHaveLength(2);
```

- [ ] **Step 1d: Give the null-ranks test populated sleep data**

The test titled `'shows fallback dashes for null ranks and missing best-day'` asserts exact counts of `—` and `0 steps · —`. Add sleep handlers that return NON-null data so the sleep section adds no extra dashes (its intent is steps null-rank rendering). Add these four entries to the TOP of that test's `routedMock({ ... })` object (before `/summary`):

```tsx
        '/sleep/users/lonely/summary': aliceSleepSummary,
        '/sleep/users/lonely/daily': aliceSleepDaily,
        '/sleep/users/lonely/weekly': aliceSleepWeekly,
        '/sleep/users/lonely/monthly': aliceSleepMonthly,
```

(The username in the payload is irrelevant — the sleep cards don't render it. Populated ranks/best-night mean no new `—` and no `0 steps · —`, so the existing `toHaveLength(3)` / `toHaveLength(2)` assertions stay correct.)

- [ ] **Step 1e: Add the new Sleep-section test**

Add this test inside the `describe('Summary tab (default)', ...)` block:

```tsx
it('renders a Sleep section with formatted durations', async () => {
  globalThis.fetch = routedMock(summaryMocks());

  renderAt('/u/alice');

  // Section headings (h2 text, distinct from the "All-time sleep" label)
  expect(await screen.findByText('Sleep')).toBeInTheDocument();
  expect(screen.getByText('Steps')).toBeInTheDocument();
  // Best night rendered as a duration (512 min = 8h 32m)
  expect(await screen.findByText('8h 32m')).toBeInTheDocument();
  // All-time sleep in whole hours (8520 min = 142h)
  expect(screen.getByText('142h')).toBeInTheDocument();
  // Sleep daily card uses a distinct heading
  expect(screen.getByText('Last night')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npm test -- --run src/__tests__/Profile.test.tsx`
Expected: FAIL — the new Sleep-section test (no "Sleep"/"8h 32m"/"142h"/"Last night" yet) AND the `findAllByText('This week')`/`'This month'` assertions (still only 1 each until the Sleep section renders). The null-ranks and other tests should still PASS (their sleep handlers are present but the section isn't rendered yet, so the handlers go unused).

- [ ] **Step 3: Add imports to Profile.tsx**

In `frontend/src/pages/Profile.tsx`, after the existing steps API import block, add the aliased sleep imports and the duration helper:

```tsx
import {
  getUserDaily as getSleepDaily,
  getUserWeekly as getSleepWeekly,
  getUserMonthly as getSleepMonthly,
  getUserSummary as getSleepSummary,
  type UserDailyResponse as SleepDailyResponse,
  type UserWeeklyResponse as SleepWeeklyResponse,
  type UserMonthlyResponse as SleepMonthlyResponse,
  type UserSummaryResponse as SleepSummaryResponse,
} from '@/api/sleep';
```

Update the existing `import { ... } from '@/lib/dates';` to also import `formatDuration`:

```tsx
import {
  currentDate,
  formatDateMedium,
  formatDuration,
  formatTimestampDate,
} from '@/lib/dates';
```

- [ ] **Step 4: Add the sleep card components**

In `frontend/src/pages/Profile.tsx`, after the `TodayCard` component (just before the `const TABS = [...]` line), add:

```tsx
function formatSleepHours(minutes: number): string {
  return `${Math.round(minutes / 60)}h`;
}

function SleepStatStrip({ data }: { data: SleepSummaryResponse }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <StatCard
        label="All-time sleep"
        value={formatSleepHours(data.total_minutes_all_time)}
      />
      <StatCard label="Nights logged" value={formatNumber(data.nights_logged)} />
      <StatCard
        label="All-time rank"
        value={data.rank_all_time !== null ? `#${data.rank_all_time}` : '—'}
      />
      <StatCard
        label="Best night"
        value={data.best_night ? formatDuration(data.best_night.total) : '—'}
        sub={
          data.best_night ? formatHeadingDate(data.best_night.date) : undefined
        }
      />
    </div>
  );
}

function SleepTodayCard({ data }: { data: SleepDailyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-display text-2xl tracking-tight">Last night</h2>
        <span className="label-mono text-muted-foreground">
          {data.rank_today !== null ? `#${data.rank_today}` : '—'}
        </span>
      </div>
      <div className="font-display text-4xl mt-2 tabular-nums">
        {data.total > 0 ? formatDuration(data.total) : '—'}
      </div>
      <div className="label-mono text-muted-foreground mt-1">
        {data.post === null ? 'No sleep logged.' : 'Logged'}
      </div>
    </Card>
  );
}

function SleepThisWeekCard({ data }: { data: SleepWeeklyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="font-display text-2xl tracking-tight">This week</h2>
        <span className="label-mono text-muted-foreground">
          {formatDuration(data.weekly_total)} ·{' '}
          {data.rank_this_week !== null ? `#${data.rank_this_week}` : '—'}
        </span>
      </div>
      <DailyBars
        days={data.daily_breakdown}
        cols={7}
        formatValue={formatDuration}
        unit=""
      />
    </Card>
  );
}

function SleepThisMonthCard({ data }: { data: SleepMonthlyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="font-display text-2xl tracking-tight">This month</h2>
        <span className="label-mono text-muted-foreground">
          {formatDuration(data.monthly_total)} ·{' '}
          {data.rank_this_month !== null ? `#${data.rank_this_month}` : '—'}
        </span>
      </div>
      {data.daily_breakdown.length === 0 ? (
        <div className="label-mono text-muted-foreground italic">
          No sleep this month yet.
        </div>
      ) : (
        <DailyBars
          days={data.daily_breakdown}
          formatValue={formatDuration}
          unit=""
        />
      )}
    </Card>
  );
}
```

- [ ] **Step 5: Add sleep queries + render the two sections in `SummaryPanel`**

In `SummaryPanel`, after the existing `monthly` query (the `useQuery` for `['steps', 'users', username, 'monthly', month]`), add four sleep queries:

```tsx
  const sleepSummary = useQuery({
    queryKey: ['sleep', 'users', username, 'summary'],
    queryFn: () => getSleepSummary(username),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });

  const sleepDaily = useQuery({
    queryKey: ['sleep', 'users', username, 'daily', today],
    queryFn: () => getSleepDaily(username, today),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });

  const sleepWeekly = useQuery({
    queryKey: ['sleep', 'users', username, 'weekly'],
    queryFn: () => getSleepWeekly(username),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });

  const sleepMonthly = useQuery({
    queryKey: ['sleep', 'users', username, 'monthly', month],
    queryFn: () => getSleepMonthly(username, month),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });
```

Then replace the `SummaryPanel` `return (...)` block with the version below — it wraps the existing steps cards in a "Steps" section and adds a "Sleep" section:

```tsx
  return (
    <div className="space-y-8">
      <section className="space-y-6">
        <h2 className="label-mono text-muted-foreground">Steps</h2>
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
      </section>

      <section className="space-y-6">
        <h2 className="label-mono text-muted-foreground">Sleep</h2>
        {sleepSummary.isPending ? (
          <StatStripSkeleton />
        ) : sleepSummary.isError ? (
          <ErrorView
            error={sleepSummary.error}
            onRetry={() => sleepSummary.refetch()}
          />
        ) : (
          <SleepStatStrip data={sleepSummary.data} />
        )}

        {sleepDaily.isPending ? (
          <CardSkeleton heightClass="h-20" />
        ) : sleepDaily.isError ? (
          <ErrorView
            error={sleepDaily.error}
            onRetry={() => sleepDaily.refetch()}
          />
        ) : (
          <SleepTodayCard data={sleepDaily.data} />
        )}

        {sleepWeekly.isPending ? (
          <CardSkeleton heightClass="h-32" />
        ) : sleepWeekly.isError ? (
          <ErrorView
            error={sleepWeekly.error}
            onRetry={() => sleepWeekly.refetch()}
          />
        ) : (
          <SleepThisWeekCard data={sleepWeekly.data} />
        )}

        {sleepMonthly.isPending ? (
          <CardSkeleton heightClass="h-32" />
        ) : sleepMonthly.isError ? (
          <ErrorView
            error={sleepMonthly.error}
            onRetry={() => sleepMonthly.refetch()}
          />
        ) : (
          <SleepThisMonthCard data={sleepMonthly.data} />
        )}
      </section>
    </div>
  );
```

- [ ] **Step 6: Run the Profile test to verify it passes**

Run: `cd frontend && npm test -- --run src/__tests__/Profile.test.tsx`
Expected: PASS — "Sleep" + "Steps" headings present, "8h 32m" (best night) and "142h" (all-time) render.

- [ ] **Step 7: Full frontend suite + typecheck**

Run: `cd frontend && npx tsc --noEmit && npm test -- --run`
Expected: PASS — all suites. The test edits in Steps 1b–1d already cover every existing Profile test that mounts `SummaryPanel`. If a stray Profile test still fails because its custom `routedMock` map lacks `/sleep/...` handlers (and it renders `SummaryPanel`), add the four sleep builders to that test's map, keyed by full `/sleep/...` paths placed first.

- [ ] **Step 8: Build (CI parity)**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/Profile.tsx frontend/src/__tests__/Profile.test.tsx
git commit -m "feat(frontend): Sleep stats section on profile pages"
```

---

## Final verification

- [ ] **Backend:** `cd backend && python -m pytest tests/ -q` → all pass.
- [ ] **Frontend:** `cd frontend && npx tsc --noEmit && npm test -- --run && npm run build` → all pass.
- [ ] Open a PR from `worktree-sleep-feed-and-pages` into `main`; CI (backend pytest + frontend vitest + build) should be green.

## Self-review notes (spec coverage)

- D1 (sleep write → feed post, same txn, body+details, wake_time ts) → **Task 1**.
- D2 (SleepPost component + both dispatch sites) → **Task 4**.
- D3 (api/sleep.ts per-user wrapper) → **Task 3**.
- D4 (one Summary tab, Steps + Sleep stacked sections, minutes as `7h 32m`) → **Tasks 2, 5, 6**.
- Out-of-scope items (Leaderboard sleep tab, milestones/streaks, iOS Shortcut) intentionally have no tasks.
