# Users-page Hover Prefetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hovering or keyboard-focusing a row on the Users list warms that user's 8 Summary queries in the React Query cache, so opening their profile renders instantly.

**Architecture:** Extract the 8 per-user Summary query definitions (steps + sleep × summary/today/week/month) into one shared module so the Users-list prefetch and the Profile page reference identical query keys. `UserRow` calls `queryClient.prefetchQuery` for those 8 queries on `mouseEnter`/`focus`. Profile is refactored to consume the same builders so keys can't drift. Frontend-only; no backend changes.

**Tech Stack:** React 19, TypeScript, @tanstack/react-query v5, react-router-dom v7, Vitest + React Testing Library.

**Spec:** `docs/superpowers/specs/2026-06-01-users-hover-prefetch-design.md`

---

**Setup (before Task 1):** This work must land on a feature branch (synzoia CLAUDE.md: feature branches, CI gates merge to `main`). From the repo root:

```bash
git checkout main && git pull --ff-only origin main
git checkout -b feat/users-hover-prefetch
```

All commands below run from `frontend/` unless noted. Run a single test file with:
`npm test -- --run <path>` (Vitest).

## File Structure

- **Create** `frontend/src/api/userSummaryQueries.ts` — single source of truth: one builder per Summary query + a `userSummaryQueries(u, today, month)` aggregator. Returns React Query option objects usable by both `useQuery` and `prefetchQuery`.
- **Create** `frontend/src/api/__tests__/userSummaryQueries.test.ts` — contract test pinning the 8 query keys.
- **Modify** `frontend/src/lib/dates.ts` — add `currentMonthYYYYMM()` (CT-anchored, derived from `currentDate()`).
- **Modify** `frontend/src/lib/__tests__/dates.test.ts` — test for `currentMonthYYYYMM()`.
- **Modify** `frontend/src/pages/Profile.tsx` — consume the shared builders for its 9 `useQuery` calls; import `currentMonthYYYYMM` from dates; delete the local copy.
- **Modify** `frontend/src/pages/Users.tsx` — `UserRow` prefetches on `mouseEnter`/`focus`.
- **Modify** `frontend/src/__tests__/Users.test.tsx` — test that hover/focus fires prefetch.

---

### Task 1: `currentMonthYYYYMM()` in lib/dates.ts

**Files:**
- Modify: `frontend/src/lib/dates.ts`
- Test: `frontend/src/lib/__tests__/dates.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/lib/__tests__/dates.test.ts` (keep existing imports; add `currentMonthYYYYMM` to the import from `@/lib/dates`):

```ts
import { currentDate, currentMonthYYYYMM } from '@/lib/dates';

describe('currentMonthYYYYMM', () => {
  it('returns the YYYY-MM prefix of the CT current date', () => {
    expect(currentMonthYYYYMM()).toBe(currentDate().slice(0, 7));
  });

  it('matches the YYYY-MM shape', () => {
    expect(currentMonthYYYYMM()).toMatch(/^\d{4}-\d{2}$/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/lib/__tests__/dates.test.ts`
Expected: FAIL — `currentMonthYYYYMM is not a function` (or import error).

- [ ] **Step 3: Implement**

Append to `frontend/src/lib/dates.ts` (after `currentDate` / `localDate`, before `formatDateLong`):

```ts
/**
 * Current month as YYYY-MM in the app timezone. Derived from
 * currentDate() so it shares the same CT anchor — used as the `?month=`
 * key for monthly endpoints.
 */
export function currentMonthYYYYMM(): string {
  return currentDate().slice(0, 7);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run src/lib/__tests__/dates.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/dates.ts frontend/src/lib/__tests__/dates.test.ts
git commit -m "feat(dates): add CT-anchored currentMonthYYYYMM helper"
```

---

### Task 2: Shared user-summary query builders

**Files:**
- Create: `frontend/src/api/userSummaryQueries.ts`
- Test: `frontend/src/api/__tests__/userSummaryQueries.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/api/__tests__/userSummaryQueries.test.ts`:

```ts
import { describe, expect, it } from 'vitest';

import { userSummaryQueries } from '@/api/userSummaryQueries';

describe('userSummaryQueries', () => {
  it('produces the 8 Summary query keys Profile uses', () => {
    const keys = userSummaryQueries('alice', '2026-06-01', '2026-06').map(
      (q) => q.queryKey,
    );
    expect(keys).toEqual([
      ['steps', 'users', 'alice', 'summary'],
      ['steps', 'users', 'alice', 'daily', '2026-06-01'],
      ['steps', 'users', 'alice', 'weekly'],
      ['steps', 'users', 'alice', 'monthly', '2026-06'],
      ['sleep', 'users', 'alice', 'summary'],
      ['sleep', 'users', 'alice', 'daily', '2026-06-01'],
      ['sleep', 'users', 'alice', 'weekly'],
      ['sleep', 'users', 'alice', 'monthly', '2026-06'],
    ]);
  });

  it('each query has a callable queryFn and no-retry options', () => {
    for (const q of userSummaryQueries('bob', '2026-06-01', '2026-06')) {
      expect(typeof q.queryFn).toBe('function');
      expect(q.staleTime).toBe(30_000);
      expect(q.retry).toBe(false);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/api/__tests__/userSummaryQueries.test.ts`
Expected: FAIL — cannot resolve `@/api/userSummaryQueries`.

- [ ] **Step 3: Implement**

Create `frontend/src/api/userSummaryQueries.ts`:

```ts
/**
 * Single source of truth for the per-user Summary queries.
 *
 * The Profile page (Summary tab) and the Users-list hover prefetch BOTH
 * use these builders, so their React Query keys are guaranteed identical
 * — otherwise a prefetch would warm cache entries the Profile page never
 * reads. `today` / `month` are passed in (from lib/dates) so the
 * date-stamped keys match across call sites.
 */
import {
  getUserSummary as getStepsSummary,
  getUserDaily as getStepsDaily,
  getUserWeekly as getStepsWeekly,
  getUserMonthly as getStepsMonthly,
} from '@/api/steps';
import {
  getUserSummary as getSleepSummary,
  getUserDaily as getSleepDaily,
  getUserWeekly as getSleepWeekly,
  getUserMonthly as getSleepMonthly,
} from '@/api/sleep';

const STALE = 30_000;

export const stepsSummaryQuery = (u: string) => ({
  queryKey: ['steps', 'users', u, 'summary'] as const,
  queryFn: () => getStepsSummary(u),
  staleTime: STALE,
  retry: false as const,
});

export const stepsDailyQuery = (u: string, today: string) => ({
  queryKey: ['steps', 'users', u, 'daily', today] as const,
  queryFn: () => getStepsDaily(u, today),
  staleTime: STALE,
  retry: false as const,
});

export const stepsWeeklyQuery = (u: string) => ({
  queryKey: ['steps', 'users', u, 'weekly'] as const,
  queryFn: () => getStepsWeekly(u),
  staleTime: STALE,
  retry: false as const,
});

export const stepsMonthlyQuery = (u: string, month: string) => ({
  queryKey: ['steps', 'users', u, 'monthly', month] as const,
  queryFn: () => getStepsMonthly(u, month),
  staleTime: STALE,
  retry: false as const,
});

export const sleepSummaryQuery = (u: string) => ({
  queryKey: ['sleep', 'users', u, 'summary'] as const,
  queryFn: () => getSleepSummary(u),
  staleTime: STALE,
  retry: false as const,
});

export const sleepDailyQuery = (u: string, today: string) => ({
  queryKey: ['sleep', 'users', u, 'daily', today] as const,
  queryFn: () => getSleepDaily(u, today),
  staleTime: STALE,
  retry: false as const,
});

export const sleepWeeklyQuery = (u: string) => ({
  queryKey: ['sleep', 'users', u, 'weekly'] as const,
  queryFn: () => getSleepWeekly(u),
  staleTime: STALE,
  retry: false as const,
});

export const sleepMonthlyQuery = (u: string, month: string) => ({
  queryKey: ['sleep', 'users', u, 'monthly', month] as const,
  queryFn: () => getSleepMonthly(u, month),
  staleTime: STALE,
  retry: false as const,
});

/** All 8 Summary-tab queries for a user, in display order. */
export function userSummaryQueries(u: string, today: string, month: string) {
  return [
    stepsSummaryQuery(u),
    stepsDailyQuery(u, today),
    stepsWeeklyQuery(u),
    stepsMonthlyQuery(u, month),
    sleepSummaryQuery(u),
    sleepDailyQuery(u, today),
    sleepWeeklyQuery(u),
    sleepMonthlyQuery(u, month),
  ];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run src/api/__tests__/userSummaryQueries.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/userSummaryQueries.ts frontend/src/api/__tests__/userSummaryQueries.test.ts
git commit -m "feat(api): shared per-user Summary query builders"
```

---

### Task 3: Refactor Profile.tsx to use the shared builders

This is a behavior-preserving refactor — the existing `Profile.test.tsx` is the safety net. No new test; we keep it green before and after.

**Files:**
- Modify: `frontend/src/pages/Profile.tsx`
- Test (regression): `frontend/src/__tests__/Profile.test.tsx`

- [ ] **Step 1: Establish green baseline**

Run: `npm test -- --run src/__tests__/Profile.test.tsx`
Expected: PASS (baseline before refactor).

- [ ] **Step 2: Replace the steps/sleep imports and add the builder import**

In `frontend/src/pages/Profile.tsx`, the `getUser*` value imports from `@/api/steps` and `@/api/sleep` are now only needed for their **types**. Change those two import blocks to type-only, and add the builder import. Replace:

```ts
import {
  getUserDaily,
  getUserMonthly,
  getUserSummary,
  getUserWeekly,
  type UserDailyResponse,
  type UserMonthlyResponse,
  type UserSummaryResponse,
  type UserWeeklyResponse,
} from '@/api/steps';
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

with:

```ts
import type {
  UserDailyResponse,
  UserMonthlyResponse,
  UserSummaryResponse,
  UserWeeklyResponse,
} from '@/api/steps';
import type {
  UserDailyResponse as SleepDailyResponse,
  UserWeeklyResponse as SleepWeeklyResponse,
  UserMonthlyResponse as SleepMonthlyResponse,
  UserSummaryResponse as SleepSummaryResponse,
} from '@/api/sleep';
import {
  stepsSummaryQuery,
  stepsDailyQuery,
  stepsWeeklyQuery,
  stepsMonthlyQuery,
  sleepSummaryQuery,
  sleepDailyQuery,
  sleepWeeklyQuery,
  sleepMonthlyQuery,
} from '@/api/userSummaryQueries';
```

- [ ] **Step 3: Import `currentMonthYYYYMM` from dates and delete the local copy**

Add `currentMonthYYYYMM` to the existing `@/lib/dates` import:

```ts
import {
  currentDate,
  currentMonthYYYYMM,
  formatDateMedium,
  formatDuration,
  formatTimestampDate,
} from '@/lib/dates';
```

Then delete the local function definition in `Profile.tsx`:

```ts
function currentMonthYYYYMM(): string {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  return `${yyyy}-${mm}`;
}
```

- [ ] **Step 4: Rewrite the 8 SummaryPanel queries using the builders**

In `SummaryPanel`, replace the eight `useQuery({...})` blocks (the four `steps`/`sleep` ones each) with builder spreads. The `today` and `month` consts at the top of `SummaryPanel` stay. New query declarations:

```ts
  const summary = useQuery({ ...stepsSummaryQuery(username), enabled: !!username });
  const daily = useQuery({ ...stepsDailyQuery(username, today), enabled: !!username });
  const weekly = useQuery({ ...stepsWeeklyQuery(username), enabled: !!username });
  const monthly = useQuery({ ...stepsMonthlyQuery(username, month), enabled: !!username });

  const sleepSummary = useQuery({ ...sleepSummaryQuery(username), enabled: !!username });
  const sleepDaily = useQuery({ ...sleepDailyQuery(username, today), enabled: !!username });
  const sleepWeekly = useQuery({ ...sleepWeeklyQuery(username), enabled: !!username });
  const sleepMonthly = useQuery({ ...sleepMonthlyQuery(username, month), enabled: !!username });
```

Everything downstream (`summary.data`, `summary.isPending`, `summary.refetch`, the `StatStrip`/`TodayCard`/etc. components) is unchanged.

- [ ] **Step 5: Rewrite the top-level Profile 404-detection query**

In the `Profile` component, replace:

```ts
  const summary = useQuery({
    queryKey: ['steps', 'users', username, 'summary'],
    queryFn: () => getUserSummary(username),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });
```

with:

```ts
  const summary = useQuery({ ...stepsSummaryQuery(username), enabled: !!username });
```

- [ ] **Step 6: Typecheck + run regression test**

Run: `npm run typecheck`
Expected: no errors.

Run: `npm test -- --run src/__tests__/Profile.test.tsx`
Expected: PASS (same behavior, builder-sourced keys).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Profile.tsx
git commit -m "refactor(profile): source Summary query keys from shared builders"
```

---

### Task 4: Prefetch on hover/focus in Users.tsx

**Files:**
- Modify: `frontend/src/pages/Users.tsx`
- Test: `frontend/src/__tests__/Users.test.tsx`

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/__tests__/Users.test.tsx`. Update the top imports to add `fireEvent` and the steps/sleep API modules:

```ts
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
// ...existing imports...
import * as stepsApi from '@/api/steps';
import * as sleepApi from '@/api/sleep';
```

Add this test inside `describe('Users page', ...)`:

```ts
  it('prefetches a user\'s summary data on hover', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      profiles: [
        { username: 'alice', join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 9000 },
      ],
    });
    const stepsSummary = vi
      .spyOn(stepsApi, 'getUserSummary')
      .mockResolvedValue({} as never);
    const sleepSummary = vi
      .spyOn(sleepApi, 'getUserSummary')
      .mockResolvedValue({} as never);
    // Silence the rest of the prefetch fan-out.
    vi.spyOn(stepsApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserMonthly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserMonthly').mockResolvedValue({} as never);

    renderUsers();
    const link = await screen.findByRole('link', { name: /alice/ });

    // Nothing prefetched until the row is hovered.
    expect(stepsSummary).not.toHaveBeenCalled();

    fireEvent.mouseEnter(link);

    await waitFor(() => expect(stepsSummary).toHaveBeenCalledWith('alice'));
    expect(sleepSummary).toHaveBeenCalledWith('alice');
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/__tests__/Users.test.tsx`
Expected: FAIL — `stepsSummary` not called after `mouseEnter` (no prefetch wired yet).

- [ ] **Step 3: Implement the prefetch in UserRow**

In `frontend/src/pages/Users.tsx`, update imports:

```ts
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import ErrorCard from '@/components/ui/ErrorCard';
import PageHeader from '@/components/ui/PageHeader';
import RowListSkeleton from '@/components/ui/RowListSkeleton';
import { getProfiles, type ProfileListEntry } from '@/api/profiles';
import { userSummaryQueries } from '@/api/userSummaryQueries';
import { currentDate, currentMonthYYYYMM } from '@/lib/dates';
```

Replace the `UserRow` component with:

```ts
function UserRow({ profile }: { profile: ProfileListEntry }) {
  const queryClient = useQueryClient();

  // Warm the 8 Summary-tab queries so clicking through renders instantly.
  // prefetchQuery respects staleTime, so repeat hovers within 30s are
  // no-ops, and a failed prefetch is swallowed (Profile just loads
  // normally on click).
  const prefetch = () => {
    const today = currentDate();
    const month = currentMonthYYYYMM();
    for (const q of userSummaryQueries(profile.username, today, month)) {
      queryClient.prefetchQuery(q);
    }
  };

  return (
    <li className="border-b border-border/60 last:border-b-0">
      <Link
        to={`/u/${encodeURIComponent(profile.username)}`}
        onMouseEnter={prefetch}
        onFocus={prefetch}
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run src/__tests__/Users.test.tsx`
Expected: PASS (all Users tests, including the new prefetch test).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Users.tsx frontend/src/__tests__/Users.test.tsx
git commit -m "feat(users): prefetch user summary on row hover/focus"
```

---

### Task 5: Full verification

**Files:** none (verification only).

- [ ] **Step 1: Typecheck**

Run: `npm run typecheck`
Expected: no errors.

- [ ] **Step 2: Full test suite**

Run: `npm test -- --run`
Expected: all suites PASS.

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: build succeeds (this is what CI gates on).

- [ ] **Step 4: Manual smoke (optional but recommended)**

Run: `npm run dev`, open `/users`, hover a row, then click it. The profile Summary should render with no skeleton flash. In devtools Network, confirm the 8 requests fire on hover, not on click.

- [ ] **Step 5: Push and open PR**

```bash
git push -u origin feat/users-hover-prefetch
gh pr create --fill
```

---

## Self-Review

**1. Spec coverage:**
- Hover/focus prefetch of 8 Summary queries → Task 4. ✓
- Shared query-builder module (key parity) → Task 2, consumed in Tasks 3 & 4. ✓
- `currentMonthYYYYMM` moved to `lib/dates.ts` → Task 1, used in Task 3 (Profile) & Task 4 (Users). ✓
- Profile refactor to consume builders → Task 3. ✓
- Error handling (prefetch never throws; retry:false) → builders carry `retry: false` (Task 2); `prefetchQuery` swallows errors by design (documented in Task 4 code comment). ✓
- Testing: builder key contract (Task 2), hover fires prefetch (Task 4), Profile regression (Task 3). ✓
- Out of scope (Feed prefetch, eager-all, bundle endpoint) — correctly excluded; no tasks touch them. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code; every run step shows the command + expected result. ✓

**3. Type consistency:** Builder names (`stepsSummaryQuery`, `stepsDailyQuery`, `stepsWeeklyQuery`, `stepsMonthlyQuery`, `sleepSummaryQuery`, `sleepDailyQuery`, `sleepWeeklyQuery`, `sleepMonthlyQuery`, `userSummaryQueries`) are identical across Tasks 2, 3, 4. Query keys in the Task 2 test match the keys Profile used pre-refactor (steps/sleep × summary/daily+today/weekly/monthly+month). `currentMonthYYYYMM` signature `() => string` consistent across Tasks 1, 3, 4. ✓
