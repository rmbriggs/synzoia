# Users-page hover prefetch — design

**Date:** 2026-06-01
**Status:** Approved (pending spec review)
**Area:** frontend (React + React Query)

## Problem

On the Users list (`/users`, `pages/Users.tsx`), clicking a user navigates to their
profile (`/u/:username`, `pages/Profile.tsx`). The profile's default **Summary** tab
fires **8 separate requests** on mount — steps and sleep, each as summary / today /
this-week / this-month:

- `['steps','users',<u>,'summary']`
- `['steps','users',<u>,'daily',<today>]`
- `['steps','users',<u>,'weekly']`
- `['steps','users',<u>,'monthly',<month>]`
- `['sleep','users',<u>,'summary']`
- `['sleep','users',<u>,'daily',<today>]`
- `['sleep','users',<u>,'weekly']`
- `['sleep','users',<u>,'monthly',<month>]`

That fan-out to the serverless backend is the perceived lag when opening a profile.
(The **Feed** tab is a separate, lazily-loaded 9th query and is explicitly out of scope.)

## Goal

When the user hovers or keyboard-focuses a row on the Users list, warm that user's 8
Summary queries in the React Query cache, so clicking through renders the Summary tab
instantly (no skeletons), with no wait.

## Approach

**Hover/focus prefetch** (chosen over eager-prefetch-all and over a backend bundle
endpoint). Rationale: hovering precedes a click by ~200 ms, which is enough to warm the
cache so the click feels instant, while firing requests only for the user about to be
clicked — far less load than prefetching every listed user up front. Frontend-only; no
backend change.

Trade-offs accepted: no hover on touchscreens (those users simply get today's
behavior — load on click), and it does not literally preload every user. Both are fine
for this app's size and usage.

## Components & changes

### 1. New `src/api/userSummaryQueries.ts` — single source of truth for the 8 queries

Exports one small builder per query, each returning React Query options with the **exact**
key/fn/`staleTime`/`retry` the Profile page uses today:

```ts
export const stepsSummaryQuery = (u: string) => ({
  queryKey: ['steps', 'users', u, 'summary'] as const,
  queryFn: () => getUserSummary(u),
  staleTime: 30_000,
  retry: false as const,
});
// ...stepsDailyQuery(u, today), stepsWeeklyQuery(u), stepsMonthlyQuery(u, month),
//    sleepSummaryQuery(u), sleepDailyQuery(u, today), sleepWeeklyQuery(u), sleepMonthlyQuery(u, month)

export function userSummaryQueries(u: string, today: string, month: string) {
  return [
    stepsSummaryQuery(u), stepsDailyQuery(u, today), stepsWeeklyQuery(u), stepsMonthlyQuery(u, month),
    sleepSummaryQuery(u), sleepDailyQuery(u, today), sleepWeeklyQuery(u), sleepMonthlyQuery(u, month),
  ];
}
```

The builders deliberately omit `enabled` (prefetch is called explicitly; Profile adds
`enabled: !!username`).

### 2. `src/pages/Users.tsx` — prefetch on hover/focus

`UserRow` gets `useQueryClient()` and adds `onMouseEnter` + `onFocus` to the `<Link>`:

```ts
const today = currentDate();
const month = currentMonthYYYYMM();
const warm = () =>
  userSummaryQueries(profile.username, today, month)
    .forEach((q) => queryClient.prefetchQuery(q));
// <Link ... onMouseEnter={warm} onFocus={warm}>
```

`prefetchQuery` respects `staleTime`, so repeated hovers within 30 s are no-ops. Nothing
else about the list rendering changes.

### 3. `src/pages/Profile.tsx` — consume the shared builders (key-parity refactor)

The 9 inline `useQuery` calls (the 8 Summary queries in `SummaryPanel` + the top-level
404-detection `summary` query) are changed to spread the shared builders, e.g.:

```ts
const summary = useQuery({ ...stepsSummaryQuery(username), enabled: !!username });
```

Each query stays individually typed and wired to its component (StatStrip, TodayCard,
SleepStatStrip, …) — only the key+fn definitions move into the shared module. This is the
step that makes prefetch reliable: prefetch and Profile reference identical keys.
Without it, the keys can silently drift and the prefetched cache entries never match.

### 4. `src/lib/dates.ts` — move `currentMonthYYYYMM()`

`currentMonthYYYYMM()` currently lives as a local function in `Profile.tsx`. Move it into
`lib/dates.ts` next to `currentDate()` so Profile and the Users prefetch derive the same
`today`/`month` values (the daily/monthly query keys are date-stamped and must match).

## Data flow

1. Hover/focus a row → 8 `prefetchQuery` calls populate the cache under the canonical keys.
2. Click → navigate to `/u/:username` → `Profile` mounts.
3. Profile's `useQuery`s find fresh cache entries → immediate render, no skeletons.
   (If >30 s elapsed, cached data still renders instantly and revalidates in the
   background — still no spinner.)

## Error handling

`prefetchQuery` never throws to the UI. A failed prefetch (network, etc.) simply leaves
the cache cold, and Profile falls back to its normal on-mount load (skeleton → fetch). The
Users list is never broken by a prefetch failure. `retry: false` is preserved so hovering
does not trigger retry storms.

## Testing

- **New `src/api/__tests__/userSummaryQueries.test.ts`** — assert the builders produce the
  exact 8 query keys for a given username (and the date-stamped ones include the passed
  `today`/`month`). This is the contract that keeps prefetch and Profile in sync.
- **Extend `src/__tests__/Users.test.tsx`** — fire `mouseEnter` / `focus` on a row and
  assert the user's Summary queries are fetched (spy the api modules or the query client),
  i.e. prefetch fired on hover/focus.
- **Existing `src/__tests__/Profile.test.tsx`** — regression guard that Profile still
  renders correctly after the builder refactor.

## Files

- New: `src/api/userSummaryQueries.ts`, `src/api/__tests__/userSummaryQueries.test.ts`
- Edit: `src/pages/Users.tsx`, `src/pages/Profile.tsx`, `src/lib/dates.ts`
- Extend: `src/__tests__/Users.test.tsx`
- No backend changes.

## Out of scope

- Prefetching the **Feed** tab (separate lazy query).
- An eager "prefetch all listed users" strategy.
- A backend summary-bundle endpoint to collapse the 8 requests into 1 (a future option if
  the group grows or hover prefetch proves insufficient).
