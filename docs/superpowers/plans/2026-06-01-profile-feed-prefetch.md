# Profile Feed Prefetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prefetch a user's feed when their Profile (Summary page) mounts, so opening the Feed tab renders instantly from cache.

**Architecture:** Add a `userFeedQuery` builder to the existing shared module (`src/api/userSummaryQueries.ts`), have `FeedPanel` consume it (key parity), and add a `useEffect` in the `Profile` component that calls `queryClient.prefetchQuery(userFeedQuery(username))` on mount. Frontend-only; extends PR #46 on the `feat/users-hover-prefetch` branch.

**Tech Stack:** React 19, TypeScript, @tanstack/react-query v5, Vitest + React Testing Library.

**Spec:** `docs/superpowers/specs/2026-06-01-profile-feed-prefetch-design.md`

---

**Setup:** Work on the already-checked-out `feat/users-hover-prefetch` branch (this extends PR #46). Do NOT create a new branch. All commands run from `frontend/`. Run a single test file with `npm test -- --run <path>`.

## File Structure

- **Modify** `frontend/src/api/userSummaryQueries.ts` — add `userFeedQuery` builder (+ `getUserFeed` import, `FEED_LIMIT` const, broadened doc comment).
- **Modify** `frontend/src/api/__tests__/userSummaryQueries.test.ts` — contract test for the feed key/options.
- **Modify** `frontend/src/pages/Profile.tsx` — `FeedPanel` uses the builder; `Profile` prefetches the feed on mount.
- **Modify** `frontend/src/__tests__/Profile.test.tsx` — test that the feed is fetched on Summary mount.

---

### Task 1: Add `userFeedQuery` builder

**Files:**
- Modify: `frontend/src/api/userSummaryQueries.ts`
- Test: `frontend/src/api/__tests__/userSummaryQueries.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/api/__tests__/userSummaryQueries.test.ts`. Update the import to also pull in `userFeedQuery`:

```ts
import { userSummaryQueries, userFeedQuery } from '@/api/userSummaryQueries';
```

Add this describe block:

```ts
describe('userFeedQuery', () => {
  it('matches the FeedPanel query key and options', () => {
    const q = userFeedQuery('alice');
    expect(q.queryKey).toEqual(['posts', 'users', 'alice', 'feed', 50]);
    expect(q.staleTime).toBe(30_000);
    expect(typeof q.queryFn).toBe('function');
    // Intentionally NOT set — FeedPanel uses the default retry, unlike
    // the summary builders. Pinning this prevents an accidental change.
    expect('retry' in q).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/api/__tests__/userSummaryQueries.test.ts`
Expected: FAIL — `userFeedQuery` is not exported.

- [ ] **Step 3: Implement**

In `frontend/src/api/userSummaryQueries.ts`:

(a) Update the top doc comment's first line from describing only Summary queries to: `Single source of truth for the per-user profile query builders (summary + feed).` (keep the rest of the comment).

(b) Add the import for `getUserFeed` after the sleep import block:

```ts
import { getUserFeed } from '@/api/posts';
```

(c) Add a `FEED_LIMIT` constant next to `STALE`:

```ts
const FEED_LIMIT = 50;
```

(d) Add the builder (place it after the 8 summary builders, before the `userSummaryQueries` aggregator):

```ts
/**
 * The user's feed query (Profile's Feed tab). No `retry` override — it
 * mirrors FeedPanel's existing query, which uses the default retry
 * (the summary builders set retry:false; the feed one does not).
 */
export const userFeedQuery = (u: string) => ({
  queryKey: ['posts', 'users', u, 'feed', FEED_LIMIT] as const,
  queryFn: () => getUserFeed(u, FEED_LIMIT),
  staleTime: STALE,
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- --run src/api/__tests__/userSummaryQueries.test.ts`
Expected: PASS. Also run `npm run typecheck` — no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/userSummaryQueries.ts frontend/src/api/__tests__/userSummaryQueries.test.ts
git commit -m "feat(api): add userFeedQuery builder"
```

---

### Task 2: FeedPanel uses the builder + prefetch feed on Profile mount

**Files:**
- Modify: `frontend/src/pages/Profile.tsx`
- Test: `frontend/src/__tests__/Profile.test.tsx`

- [ ] **Step 1: Establish green baseline**

Run: `npm test -- --run src/__tests__/Profile.test.tsx`
Expected: PASS. (If not, STOP and report NEEDS_CONTEXT.)

- [ ] **Step 2: Write the failing test**

Add to `frontend/src/__tests__/Profile.test.tsx`, inside the `describe('Feed tab', ...)` block (after the existing feed tests):

```ts
    it('prefetches the feed when the Summary page loads (before the Feed tab is opened)', async () => {
      const fetchMock = routedMock({
        ...summaryMocks(),
        '/posts/users/': () => ok({ posts: [] }),
      });
      globalThis.fetch = fetchMock;

      // Land on the Summary tab — NOT ?tab=feed.
      renderAt('/u/alice');

      // The prefetch effect fetches the feed endpoint even though the
      // Feed tab was never opened. (On the Summary tab nothing else hits
      // /posts/users/* — the stat queries hit /steps/* and /sleep/*.)
      await waitFor(() =>
        expect(
          fetchMock.mock.calls.some(([url]) =>
            String(url).includes('/posts/users/alice'),
          ),
        ).toBe(true),
      );
    });
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npm test -- --run src/__tests__/Profile.test.tsx`
Expected: the new test FAILS — on the Summary tab the feed endpoint is never hit (no prefetch yet). Existing tests still pass.

- [ ] **Step 4: Implement**

In `frontend/src/pages/Profile.tsx`:

(a) Add `useQueryClient` to the react-query import and add a `useEffect` import. Change line 1 and add a React import:

```ts
import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
```

(b) Add `userFeedQuery` to the builder import block from `@/api/userSummaryQueries`:

```ts
import {
  stepsSummaryQuery,
  stepsDailyQuery,
  stepsWeeklyQuery,
  stepsMonthlyQuery,
  sleepSummaryQuery,
  sleepDailyQuery,
  sleepWeeklyQuery,
  sleepMonthlyQuery,
  userFeedQuery,
} from '@/api/userSummaryQueries';
```

(c) Refactor `FeedPanel`'s query (currently `useQuery({ queryKey: ['posts','users',username,'feed',50], queryFn: () => getUserFeed(username, 50), enabled: !!username, staleTime: 30_000 })`) to use the builder:

```ts
function FeedPanel({ username }: { username: string }) {
  const query = useQuery({ ...userFeedQuery(username), enabled: !!username });
```

(Leave the rest of `FeedPanel` — the isPending/isError/empty/post-dispatch rendering — unchanged. `getUserFeed` is still imported and used by the builder, but `Profile.tsx` no longer references it directly; if `getUserFeed` becomes an unused import in Profile.tsx, remove it from the `@/api/posts` import line, keeping `type FeedPost`. Let typecheck tell you.)

(d) In the `Profile` component, add the prefetch effect. Insert it right after `const { currentUser, setCurrentUser } = useCurrentUser();` and BEFORE the `if (!username)` guard (to respect the Rules of Hooks):

```ts
  const queryClient = useQueryClient();
  // Warm the feed in the background as soon as the profile loads, so the
  // Feed tab renders instantly when opened. prefetchQuery respects
  // staleTime and swallows errors, so this never affects the Summary view.
  useEffect(() => {
    if (username) queryClient.prefetchQuery(userFeedQuery(username));
  }, [queryClient, username]);
```

- [ ] **Step 5: Run test + typecheck**

Run: `npm test -- --run src/__tests__/Profile.test.tsx`
Expected: PASS (all Profile tests including the new one).
Run: `npm run typecheck`
Expected: no errors. (If `getUserFeed` is now unused in Profile.tsx, remove it from the import per 4(c) and re-run.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Profile.tsx frontend/src/__tests__/Profile.test.tsx
git commit -m "feat(profile): prefetch feed on Summary mount; FeedPanel uses shared builder"
```

---

### Task 3: Full verification + push to PR #46

**Files:** none (verification only).

- [ ] **Step 1: Typecheck** — Run: `npm run typecheck`. Expected: no errors.
- [ ] **Step 2: Full test suite** — Run: `npm test -- --run`. Expected: all suites PASS.
- [ ] **Step 3: Build** — Run: `npm run build`. Expected: succeeds.
- [ ] **Step 4: Manual smoke (optional)** — `npm run dev`, open `/u/<someone>` on the Summary tab, confirm in the Network tab that the `/posts/users/<someone>/feed` request fires immediately (before clicking Feed); click the Feed tab → renders with no skeleton.
- [ ] **Step 5: Push (updates PR #46)**

```bash
git push origin feat/users-hover-prefetch
```

The push updates the open PR #46; CI re-runs automatically.

---

## Self-Review

**1. Spec coverage:**
- `userFeedQuery` builder matching FeedPanel's exact key, `staleTime: 30_000`, no `retry` → Task 1. ✓
- FeedPanel consumes the builder (key parity) → Task 2, step 4(c). ✓
- Prefetch on Profile mount via `useEffect` + `queryClient.prefetchQuery` → Task 2, step 4(d). ✓
- Error handling (prefetch swallows errors) → relies on React Query's `prefetchQuery` Promise<void> contract; documented in the effect comment. ✓
- Tests: builder key contract (Task 1), feed fetched on Summary mount (Task 2). ✓
- Out of scope (no feed prefetch from the Users list hover, no mutations) — untouched. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code; run steps show command + expected result. The one conditional ("if `getUserFeed` becomes unused, remove it") is explicit with a concrete action and a typecheck check, not a vague placeholder. ✓

**3. Type consistency:** `userFeedQuery(u: string)` used identically in Task 1 (definition + test), Task 2 4(c) (FeedPanel), and 4(d) (prefetch). Key `['posts','users',u,'feed',50]` matches FeedPanel's pre-refactor inline key exactly. `FEED_LIMIT = 50` used in both the key and `getUserFeed` call. ✓
