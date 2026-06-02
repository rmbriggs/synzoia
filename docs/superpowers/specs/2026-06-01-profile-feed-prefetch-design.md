# Profile feed prefetch — design

**Date:** 2026-06-01
**Status:** Approved (pending spec review)
**Area:** frontend (React + React Query)
**Builds on:** `2026-06-01-users-hover-prefetch-design.md` (extends the same shared query-builder module). Ships on the same branch / PR #46.

## Problem

The Profile page (`pages/Profile.tsx`) has two tabs: **Summary** (default) and **Feed**. The hover-prefetch work made the Summary tab instant. But the **Feed** tab still loads lazily: `FeedPanel` only mounts when you switch to the Feed tab, and its query (`['posts','users',<u>,'feed',50]` via `getUserFeed(u, 50)`) fires at that moment — so opening the Feed tab shows a skeleton then a network wait.

## Goal

When you land on a user's Summary page, warm their feed in the background so switching to the Feed tab renders instantly from cache. Read-only prefetch — the feed has no in-app mutations.

## Approach

Prefetch the feed query on `Profile` mount (and whenever the viewed `username` changes), reusing the established prefetch + shared-builder pattern. Chosen over hover-on-the-Feed-tab because the explicit ask is "when I click into the summary page." Cost: one extra request per profile view even if the Feed tab is never opened — acceptable at this app's scale and matches the requested behavior.

## Components & changes

### 1. `userFeedQuery` builder in `src/api/userSummaryQueries.ts`

Add a builder returning EXACTLY what `FeedPanel` uses today, so the prefetch warms the precise key FeedPanel reads:

```ts
import { getUserFeed } from '@/api/posts';

const FEED_LIMIT = 50;

export const userFeedQuery = (u: string) => ({
  queryKey: ['posts', 'users', u, 'feed', FEED_LIMIT] as const,
  queryFn: () => getUserFeed(u, FEED_LIMIT),
  staleTime: 30_000,
});
```

Note: this builder deliberately does **not** set `retry: false` — `FeedPanel`'s current query doesn't (it uses the default retry), and this refactor must preserve that behavior. (The summary builders set `retry: false` because the original summary queries did.)

Broaden the module's top doc comment from "per-user Summary queries" to "per-user profile query builders (summary + feed)."

### 2. `FeedPanel` consumes the builder

In `Profile.tsx`, refactor `FeedPanel`'s inline query to:

```ts
const query = useQuery({ ...userFeedQuery(username), enabled: !!username });
```

Everything downstream (the `query.isPending` / `isError` / `data.posts` rendering and the post-type dispatch to RecapPost / MilestonePost / SleepPost / GenericPost) is unchanged.

### 3. Prefetch on mount in the `Profile` component

`Profile` is always mounted regardless of which tab is active, so warm the feed there. Add `useQueryClient()` and an effect keyed on `username`:

```ts
const queryClient = useQueryClient();
useEffect(() => {
  if (username) queryClient.prefetchQuery(userFeedQuery(username));
}, [queryClient, username]);
```

This runs as soon as the Summary page renders; by the time the user clicks the Feed tab, the cache is warm and `FeedPanel`'s `useQuery` resolves instantly. `prefetchQuery` respects `staleTime`, so revisits within 30 s are no-ops.

## Data flow

1. Land on `/u/:username` → `Profile` mounts → effect prefetches the feed query in the background.
2. User clicks the **Feed** tab → `FeedPanel` mounts → its `useQuery` finds the warm cache entry → renders immediately (no skeleton). If >30 s elapsed, cached data still renders instantly and revalidates in the background.

## Error handling

`prefetchQuery` never throws to the UI. A failed feed prefetch leaves the cache cold, and `FeedPanel` falls back to its normal on-mount load (skeleton → fetch) when the tab is opened. The Summary page is never affected by a prefetch failure.

## Testing

- **Builder key contract** (extend `src/api/__tests__/userSummaryQueries.test.ts`): `userFeedQuery('alice')` → `['posts','users','alice','feed',50]`, `staleTime === 30_000`, and `retry` is left unset (undefined).
- **Profile prefetches feed on mount** (extend `src/__tests__/Profile.test.tsx`): render `Profile` on the default Summary tab (do NOT switch to Feed), spy `getUserFeed`, and assert it was called with `('alice', 50)` — proving the feed warms without opening the tab.
- **FeedPanel refactor** is covered by existing `Profile.test.tsx` feed-tab assertions (regression net).

## Files

- Edit: `src/api/userSummaryQueries.ts` (add `userFeedQuery`, import `getUserFeed`, broaden doc comment)
- Edit: `src/pages/Profile.tsx` (FeedPanel uses builder; add prefetch-on-mount effect)
- Extend: `src/api/__tests__/userSummaryQueries.test.ts`, `src/__tests__/Profile.test.tsx`
- No backend changes.

## Out of scope

- Prefetching the feed for users you only hover on the Users list (we prefetch the 8 Summary queries there, not the feed — keeps the list-load light).
- Any change to how feed posts are produced or to feed pagination.
- Real "optimistic updates" in the mutation sense — the feed is read-only; there is no in-app write to optimistically reflect.

## Execution

Ships on the existing `feat/users-hover-prefetch` branch, extending **PR #46** (unmerged, same feature family).
