# Users index + per-user page restructure

**Date**: 2026-05-25
**Author**: Micah (with Claude Opus 4.7)
**Status**: Proposed

## 0. Context

The site has a per-user page at `/u/:username` (`frontend/src/pages/Profile.tsx`) showing today's + this week's stats. It does **not** have:

- A monthly summary.
- A feed filtered to a specific user.
- An index page listing everyone.

Usernames in `Feed.tsx` and `Leaderboard.tsx` already link to `/u/:username`, so click-through navigation already works in those places. The backend already exposes per-user daily, weekly, and summary endpoints, plus an unused `/api/posts/users/{username}` endpoint that filters `WHERE post.user_id = uid`. That filter is wrong for this product — posts are auto-created (milestones, recaps), not user-authored — so a useful "user feed" needs to be redefined as **posts that mention the user**.

This spec adds the missing pieces and restructures the per-user page into a two-tab layout.

## 1. Locked-in design decisions

| Decision | Choice |
|---|---|
| Per-user page approach | Restructure existing `/u/:username` with tabs (don't redesign from scratch). |
| Tab structure | Two tabs: **Summary** \| **Feed**. |
| Summary tab order (top → bottom) | StatStrip (all-time, 4 cards) → Today → This Week → This Month. |
| Monthly card visualization | Bar chart, 28–31 bars, same shape as the existing weekly card. |
| Per-user feed semantics | Posts **mentioning** the user: `post.user_id == target` UNION `type='leaderboard_recap' AND target appears in details.top`. |
| Users index layout | Compact list, leaderboard-style rows: username + all-time total. |
| Users index sort | Alphabetical by username. |
| Nav placement | "Users" entry in both top nav and bottom mobile pill. |
| URL state for tabs | Query string `?tab=summary` (default) or `?tab=feed`, via `useSearchParams`. |

## 2. Routing & navigation

**Frontend routes (`frontend/src/App.tsx`):**

- Add: `<Route path="/users" element={<Users />} />` inside the `<AppLayout />` route group.
- Keep: `<Route path="/u/:username" element={<Profile />} />` (URL unchanged; component restructured).

**Nav (`frontend/src/components/layout/AppLayout.tsx`):**

- Top nav (desktop): insert `Users` between `Leaderboard` and `Database`.
- Bottom pill (mobile): insert `Users` (lucide `Users` icon) between `Leaderboard` and `Database`.

**Smoke tests (`frontend/src/__tests__/smoke.test.tsx`):** add `/users` to the route list.

## 3. Backend changes

### 3.1 New: `GET /api/steps/users/{username}/monthly`

Pattern after `get_user_weekly`.

- File touches: `backend/app/services/steps.py` (add `get_user_monthly`), `backend/app/routes/steps.py` (add route), `backend/app/schemas/steps.py` (add `UserMonthlyResponse`).
- Query param: `month` optional, format `YYYY-MM` (default = current CT month).
- Response shape:
  ```json
  {
    "username": "micah",
    "month_start": "2026-05-01",
    "month_end": "2026-05-31",
    "monthly_total": 112400,
    "rank_this_month": 1,
    "daily_breakdown": [{"date": "2026-05-01", "total": 9123}, ...]
  }
  ```
- Aggregation: reuse `_utc_window` plus the per-CT-day MAX-of-totals pattern that `get_user_weekly` already uses. Pull rows in the padded UTC window, group by CT date in Python, max per day. (The same Python-side CT re-filter the milestone fix introduced applies here.)
- 404 with `user_not_found` when the username is unknown — same `UserNotFound` raise / `AppError` handling as `daily` / `weekly` / `summary`.

### 3.2 New: `GET /api/profiles`

- File touches: create `backend/app/routes/profiles.py` (currently the only profile handler is `POST /api/profiles` in `main.py`; promote both into the new router), `backend/app/schemas/profiles.py` (add `ProfileListEntry`, `ProfileListResponse`), `backend/app/services/profiles.py` (new file with `list_profiles`).
- No query params for v1 — user count is single-digit, no pagination needed.
- Response shape:
  ```json
  {
    "profiles": [
      {"username": "angela", "join_date": "2026-05-24T02:28:34Z", "total_steps_all_time": 21701},
      {"username": "micah",  "join_date": "2026-05-24T02:30:07Z", "total_steps_all_time": 11075}
    ]
  }
  ```
- Sort: `ORDER BY username`.
- `total_steps_all_time` reuses the same per-CT-day MAX-then-SUM aggregation `get_user_summary` does today; factor that into a shared helper (`_user_all_time_total(conn, user_id)`) so summary + this endpoint stay consistent.

### 3.3 Modified: `GET /api/posts/users/{username}` — include mentions

Current behavior (`backend/app/services/posts.py`, `list_user_feed`): `SELECT ... WHERE user_id = :uid ORDER BY timestamp DESC LIMIT :n`. Behavior change: also include `leaderboard_recap` posts where the target username appears in `details.top[*].username`.

Implementation:

1. Run the existing `WHERE user_id = :uid` query as today.
2. Run a second query: `SELECT ... WHERE type = 'leaderboard_recap'` (small set — at most one per day).
3. In Python, filter (2) to rows where any `details.top` entry has `username == target_username`.
4. Merge (1) + (2) by `timestamp DESC`, dedupe by `id` (cron currently attributes recaps to a real user, so a recap could appear in both branches), apply `limit` to the merged list.

This pattern keeps the test suite portable across Postgres and SQLite (no `jsonb @> ...` operators needed). Cost is fine for v1 — recap row count is bounded by app age in days.

`UserNotFound` resolution and `AppError` mapping stay identical.

### 3.4 Backend tests

- `backend/tests/test_steps_monthly.py` (new):
  - Returns correct `month_start` / `month_end` for the default-month and for an explicit `?month=YYYY-MM`.
  - `daily_breakdown` has one entry per day in the month, totals match per-CT-day MAX.
  - `monthly_total` equals the sum of `daily_breakdown` totals.
  - Empty month → `monthly_total: 0`, `daily_breakdown: []` (empty list, matching how `get_user_weekly` handles a week with no data).
  - 404 for unknown user.
- `backend/tests/test_profiles_list.py` (new):
  - Alphabetical ordering.
  - Includes `total_steps_all_time` per row, computed via per-CT-day MAX.
  - Users with zero steps appear with `total_steps_all_time: 0`.
  - Empty DB returns `{"profiles": []}`.
- `backend/tests/test_posts_routes.py` (extend):
  - `test_user_feed_includes_recap_where_user_appears_in_top` — insert a recap with `details.top` containing the target, assert it appears in the feed.
  - `test_user_feed_excludes_recap_where_user_not_in_top` — recap without target, assert excluded.
  - Existing cases stay unchanged.

## 4. Frontend: Users index page

**File:** `frontend/src/pages/Users.tsx`.

**API client:** add `getProfiles()` to `frontend/src/api/profiles.ts` (returns `ProfileListResponse`).

**Component shape:**

```tsx
export default function Users() {
  const query = useQuery({
    queryKey: ['profiles', 'list'],
    queryFn: getProfiles,
    staleTime: 60_000,
  });
  // loading → <RowListSkeleton />
  // error   → <ErrorCard onRetry={() => query.refetch()} />
  // empty   → <EmptyState message="No users yet." />
  // ok      → <Card><ul>{profiles.map(...UserRow)}</ul></Card>
}
```

`UserRow` is a `<Link to={`/u/${encodeURIComponent(p.username)}`}>` styled like `LeaderboardRow` without the rank column — username on the left, all-time total on the right.

**Component extraction:** the existing `LeaderboardSkeleton` in `Leaderboard.tsx` is moved/renamed to `frontend/src/components/ui/RowListSkeleton.tsx`. Both Users and Leaderboard import it. Same with `ErrorCard` — extract to `components/ui/ErrorCard.tsx`. These are pure visual refactors; behavior on `/leaderboard` is unchanged.

**Frontend tests (`frontend/src/__tests__/Users.test.tsx`):** renders rows alphabetically, row is a link with the right `to`, loading shows skeleton, error shows retry, empty shows EmptyState.

## 5. Frontend: Profile page restructure

**File:** `frontend/src/pages/Profile.tsx`.

**Layout:** header (username + join date) stays at top, outside the tabs. Below the header:

```tsx
<TabStrip
  tabs={[{key:'summary',label:'Summary'},{key:'feed',label:'Feed'}]}
  defaultKey="summary"
/>
{active === 'feed' ? <FeedPanel username={u} /> : <SummaryPanel username={u} />}
```

`active` from `useSearchParams().get('tab') ?? 'summary'` — same idiom Leaderboard uses today.

### 5.1 Summary tab

Order top → bottom: `StatStrip` (existing 4-card all-time grid) → `TodayCard` (existing) → `ThisWeekCard` (existing) → `ThisMonthCard` (**new**).

`ThisMonthCard` mirrors `ThisWeekCard` exactly, just with 28–31 bars. The inner `WeeklyBars` component currently local to `Profile.tsx` is **extracted** to `frontend/src/components/ui/DailyBars.tsx` and parameterized on the day array; both `ThisWeekCard` and `ThisMonthCard` import it. The separately-defined `WeeklyBars` in `Leaderboard.tsx` is **not** touched — it's a different component with the same name and different layout for the global page; leave it as-is for this PR to keep scope focused.

Each card runs its own React Query — `staleTime: 30_000`, `enabled: active === 'summary'`. Summary tab fires four parallel queries on mount:

- `['steps', 'users', u, 'summary']` → `getUserSummary(u)`
- `['steps', 'users', u, 'daily', today]` → `getUserDaily(u, today)`
- `['steps', 'users', u, 'weekly']` → `getUserWeekly(u)`
- `['steps', 'users', u, 'monthly']` → `getUserMonthly(u)` (**new client wrapper in `api/steps.ts`**)

Per-card error states are independent (each card renders its own `ErrorView` with retry) — if monthly fails, the other three still render. Existing behavior for daily/weekly is preserved; extended to monthly.

### 5.2 Feed tab

`<FeedPanel username={u} />`. Fires one query: `['posts', 'users', u, 'feed', 50]` → `getUserFeed(u, 50)`. `enabled: active === 'feed'`.

Renders posts using the same renderers as `/feed` (`MilestonePost`, `RecapPost`, `GenericPost`). To avoid duplication, those three components are **extracted** from `Feed.tsx` to `frontend/src/components/feed/` and re-imported by both `Feed.tsx` and the new `FeedPanel`. Behavior on `/feed` is unchanged.

Empty state: `<EmptyState message="No posts mention this user yet." />`.

### 5.3 404 handling

Unchanged. The summary-query 404 detection still gates the whole page before tabs render — if the username doesn't exist, `<NotFoundView />` renders instead of the tab strip.

### 5.4 Frontend tests (`frontend/src/__tests__/Profile.test.tsx`)

Significant rewrite (existing tests assume non-tabbed render):

- Header renders before any tab query resolves.
- Summary is the default tab.
- Clicking the Feed tab updates the URL to `?tab=feed` and renders feed posts.
- Summary tab renders StatStrip + Today + This Week + This Month cards.
- Feed tab calls `getUserFeed` and renders posts via the shared renderers.
- 404 view still gates the page when `getUserSummary` returns `user_not_found`.

`frontend/src/__tests__/Feed.test.tsx`: only the import paths for the post-renderer components change. Assertions stay identical.

## 6. Error & empty states (consolidated)

| Surface | State | Component |
|---|---|---|
| Users index | loading | `<RowListSkeleton />` |
| Users index | error | `<ErrorCard onRetry />` |
| Users index | empty | `<EmptyState message="No users yet." />` |
| Profile (any tab) | username unknown | `<NotFoundView />` (gates whole page) |
| Profile Summary | each card loading | `<CardSkeleton />` per card |
| Profile Summary | each card error | `<ErrorView onRetry />` per card |
| Profile Feed | loading | `<FeedSkeleton />` (reused from Feed) |
| Profile Feed | error | `<ErrorCard onRetry />` |
| Profile Feed | empty | `<EmptyState message="No posts mention this user yet." />` |

## 7. Migration & deploy notes

- No SQL migrations required. All three backend changes are purely query-side.
- Frontend changes are additive (new page) + non-breaking restructure (`/u/:username` URL unchanged, query keys backward-compatible). No client-side migration concerns.

## 8. Out of scope

- Pagination on `/users` (single-digit user count for v1).
- Avatar uploads / profile editing.
- "Recently active" sort options on the users index.
- Per-user weekly/monthly comparisons against the global avg.
- Tab badges (e.g., unread count on Feed tab).
- Decision on whether `/users` (or `/db`) should be auth-gated before public launch — tracked separately under the existing `project-synzoia-dbexplorer-unshipped` memory.

## 9. Implementation order (single PR, three commits)

1. **Backend**: add monthly endpoint, profiles list endpoint, extend user feed for mentions. Includes the shared `_user_all_time_total` helper. Adds the new test files.
2. **Frontend: Users index**: page, route, nav links, API client wrapper, tests. Extract `RowListSkeleton` and `ErrorCard` to `components/ui/`.
3. **Frontend: Profile tabs + monthly card**: restructure Profile.tsx, add `ThisMonthCard`, `FeedPanel`, `getUserMonthly` client. Extract post renderers to `components/feed/`. Rewrite Profile tests.

CI must pass on each commit individually. PR ships as one unit.
