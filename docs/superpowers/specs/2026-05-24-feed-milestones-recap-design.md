# Feed: step milestones + daily 6am leaderboard recap

**Date**: 2026-05-24
**Author**: Micah (with Claude Opus 4.7)
**Status**: Proposed
**Supersedes (Feed page section only)**: the implicit "today's leaderboard" behavior shipped with PR #20

## 0. Context

The Feed page (`/feed`) currently shows today's step leaderboard — same data as the Leaderboard page's Today tab. That's redundant. The Feed should be a chronological stream of *events*: things that just happened.

This spec adds two event sources and rewires `/feed` to render them:

1. **Milestone posts** — when a user crosses a step threshold (1k, 5k, 10k) for the day, the backend writes a post.
2. **Daily 6am recap** — a Vercel cron writes a post each morning congratulating the previous day's top 3.

It also commits to a richer `posts` schema (`details jsonb` + `body text`) and a few new post types, so future event sources (e.g. a sleep wake-up post) can land without another migration round.

## 1. Locked-in design decisions

These came out of the brainstorming round:

| Decision | Choice |
|---|---|
| `/feed` page surface | Pure chronological post stream. Today's leaderboard stays on `/leaderboard` only. |
| Post payload mechanism | `details jsonb` (structured) + `body text` (rendered caption) + new specific post types. |
| Cron timing for the recap | `0 11 * * *` UTC year-round — 6am CDT (Mar–Nov), 5am CST (Nov–Mar). Acceptable for class-project demo. |
| Milestone batching | Only the **highest newly-crossed threshold** per write. Idempotent per (user, day, threshold). |

## 2. Data model — migration 0007

```sql
alter table posts add column details jsonb;
alter table posts add column body    text;

alter table posts drop constraint if exists posts_type_check;
alter table posts add constraint posts_type_check
  check (type in (
    'sleep', 'steps', 'workout',           -- existing (Max's tests rely on these)
    'steps_milestone',                      -- NEW: 1k / 5k / 10k crossings
    'leaderboard_recap'                     -- NEW: 6am daily recap
  ));
```

**Why these shapes:**

- `details jsonb` carries the structured payload that's useful to the frontend (which threshold, which top-3 users + totals). Nullable because legacy post-creation paths in `services/posts.create_post` don't write it.
- `body text` is the pre-rendered caption (e.g. `"hit 10,000 steps"`). Nullable for the same reason. Storing it alongside `details` keeps the renderer dumb and makes copy editable without code changes if/when we expose a CMS-like UI. The frontend prefers `body` for display; falls back to deriving from `type` + `details` if absent.
- New post types are namespaced under the activity (`steps_milestone` keeps the `steps_` prefix so future `steps_pace_record` etc. cluster). `leaderboard_recap` is system-generated.
- Existing `sleep` / `steps` / `workout` types are kept to avoid breaking Max's `test_posts_routes.py` fixture data.

**No new indexes**: existing `posts_timestamp_idx (timestamp desc)` already serves the chronological feed read.

## 3. Backend — milestone detection on step write

Lives in the existing `POST /api/steps` handler (`routes/steps.py:create_step`). Inside the same DB transaction that inserts the step row:

```
1. Compute ct_date = _ct_date(step_row.timestamp)
2. Compute max_today = MAX(total) for (user_id, ct_date)
   — reuses the CT-bucketing logic from services/steps._daily_totals_in_range
3. SELECT distinct (details->>'threshold')::int FROM posts
   WHERE type = 'steps_milestone'
     AND user_id = :uid
     AND details->>'date' = :ct_date_iso
   → already_crossed: set[int]
4. newly_crossed = [T for T in [1000, 5000, 10000]
                    if T <= max_today AND T not in already_crossed]
5. If newly_crossed:
     threshold = max(newly_crossed)
     INSERT INTO posts (
       user_id, username, type, timestamp, details, body
     ) VALUES (
       :uid, :username, 'steps_milestone', :step_timestamp,
       jsonb_build_object('threshold', :threshold, 'date', :ct_date_iso),
       :body
     )
     where body = f"hit {threshold:,} steps"
```

**Why in the same transaction:** if the step write rolls back (e.g. CHECK constraint failure), the milestone post must roll back too — otherwise we'd have a phantom milestone for a step that doesn't exist.

**Why store `date` in `details`:** the milestone post's `timestamp` is the step row's UTC timestamp. To look up "did this user already cross 5k today?", we need to compare against the CT date the milestone bucketed to — that's `details.date`. Storing it explicitly avoids re-computing the CT bucket on every read.

**Module placement:** put `_detect_and_insert_milestone(conn, user_id, username, ct_date, max_today, step_timestamp)` in `services/steps.py` so the route stays thin.

## 4. Backend — daily recap cron

New endpoint `POST /api/cron/daily-recap` in a new module `backend/app/routes/cron.py`:

```python
@router.post("/daily-recap")
def daily_recap(authorization: Optional[str] = Header(default=None)):
    _verify_cron_secret(authorization)  # 401 on mismatch
    with db.get_engine().begin() as conn:
        return svc.write_daily_recap(conn, today=_today())
```

`_verify_cron_secret` checks `Authorization: Bearer {os.environ["CRON_SECRET"]}` against a constant-time comparison. Vercel sets this header automatically on scheduled invocations using the `CRON_SECRET` env var you set in the dashboard.

Service `services/cron.write_daily_recap(conn, today)`:

```
1. yesterday = today - 1 day  (today already comes in as CT)
2. Check for existing post:
     SELECT 1 FROM posts
     WHERE type = 'leaderboard_recap'
       AND details->>'date' = :yesterday_iso
     LIMIT 1
   → return {"skipped": "already_posted"} if found
3. Reuse svc_steps._daily_totals_in_range(conn, yesterday, yesterday)
   → list of (user_id, date, daily_total)
4. If empty: return {"skipped": "no_data"}
5. Sort by daily_total desc, username asc; take top 3
   Look up usernames via svc_steps._usernames_for
6. INSERT INTO posts (
     user_id, username, type, timestamp, details, body
   ) VALUES (
     :top1_uid, :top1_username, 'leaderboard_recap', now() at time zone 'utc',
     jsonb_build_object(
       'date', :yesterday_iso,
       'top', [{username, total}, {username, total}, {username, total}]
     ),
     'Yesterday''s top 3'
   )
   → return {"inserted": <post>}
```

**Post authorship:** the recap is attributed to the top-1 user (so `user_id` / `username` aren't null, satisfying the existing NOT NULL constraints). The `body` and `details` make it clear it's system content, not a personal post. Trade-off: if the top user gets deleted, ON DELETE CASCADE removes the recap too. Acceptable for v1.

**Vercel cron registration** — `vercel.json`:

```json
{
  "crons": [
    { "path": "/api/cron/daily-recap", "schedule": "0 11 * * *" }
  ]
}
```

Code comment notes the DST drift (5am CT during Nov–Mar).

**New env var:** `CRON_SECRET` — set via `vercel env` for Production + Preview + Development scopes. Documented in `backend/.env.example`.

## 5. Frontend — `api/posts.ts` + Feed rewrite

### `frontend/src/api/posts.ts` (new)

```ts
export interface PostDetails {
  threshold?: number;
  date?: string;
  top?: { username: string; total: number }[];
}

export interface FeedPost {
  id: number;
  user_id: number;
  username: string;
  type: 'sleep' | 'steps' | 'workout' | 'steps_milestone' | 'leaderboard_recap';
  timestamp: string;
  details: PostDetails | null;
  body: string | null;
}

export interface FeedResponse {
  posts: FeedPost[];
}

export function getFeed(limit?: number): Promise<FeedResponse> { … }
export function getUserFeed(username: string, limit?: number): Promise<FeedResponse> { … }
```

Backend's `schemas/posts.py` updates to include `details: dict | None` and `body: str | None` in `PostResponse`.

### `pages/Feed.tsx` (rewrite)

- `PageHeader` "Feed" with subtitle "Recent milestones and recaps."
- `useQuery(['posts', 'feed', 50])` → `getFeed(50)`.
- Render each post via a `<FeedPostRow>` component that switches on `type`:

  - **`steps_milestone`**: row layout
    `[trophy icon] @username  hit 10,000 steps  · 2h ago`
    Username links to `/u/:username`. Time is relative via a small `formatRelative()` helper using `APP_TIMEZONE` for "today/yesterday" determination.

  - **`leaderboard_recap`**: a slightly fatter card
    `Yesterday's top 3`
    `1. @micah  9,567`
    `2. @angela 8,340`
    `3. @bob    6,200`
    Each username links to `/u/:username`. Date subtitle shows the recap's `details.date` formatted via `formatDateMedium`.

  - **Other types** (`sleep` / `steps` / `workout`): if `body` is set, render `[icon] @username [body] · time`. Otherwise render `[icon] @username [generic] · time`. Not actively used today; render gracefully so future content doesn't break.

- States: skeleton (4 placeholder rows) while loading, retry-able error card, empty state "No posts yet. Start walking."

### `formatRelative(iso, now)` helper in `lib/dates.ts`

Renders short relative times for the feed: "just now", "5m ago", "2h ago", "yesterday", "May 21". Anchored to CT to stay consistent with the rest of the site.

## 6. Tests

### Backend

- `test_steps_write.py` additions (4 tests):
  - Step write that doesn't cross any threshold → no milestone post created.
  - Step write that crosses 1k for the first time today → milestone post inserted with threshold=1000.
  - Step write that goes 0→12000 in one shot → milestone post inserted with threshold=10000 (highest only).
  - Two consecutive writes both above the 5k threshold → only the first inserts a milestone post (idempotent).

- New `test_cron_routes.py` (4 tests):
  - Recap with three posters yesterday → inserts a post with details.top of length 3.
  - Recap with no posters yesterday → returns `{skipped: "no_data"}`, no post inserted.
  - Recap called twice in a row → second call returns `{skipped: "already_posted"}`.
  - Recap without `Authorization: Bearer <secret>` → 401, no post inserted.

### Frontend

- `Feed.test.tsx` rewritten (5 tests):
  - Stream renders a list of milestone posts, newest first.
  - Recap post renders the top-3 list correctly.
  - Empty `posts` array → empty state.
  - Failed fetch → retry-able error card.
  - Each post's username is a link to `/u/:username`.

## 7. Rollout — three PRs

| # | Title | Scope |
|---|---|---|
| 1 | `feat(backend): migration 0007 + steps_milestone posts` | Migration, schema-extends-Pydantic, milestone detection in step write, tests. Apply migration to live Supabase via MCP after merge. |
| 2 | `feat(backend): daily-recap cron at 11 UTC` | New `/api/cron/daily-recap` endpoint, `CRON_SECRET` env var, `vercel.json` cron block, tests. |
| 3 | `feat(frontend): Feed rewrite as post stream` | `api/posts.ts`, new `pages/Feed.tsx`, `formatRelative` helper, tests. |

Each is independently mergeable. After (1) and (2): milestone posts and recaps will accumulate in the DB. Until (3) merges, `/feed` is still showing the old leaderboard view — no breakage, just unchanged.

## 8. Explicitly out of scope

- The future `sleep_wake` post type and its wake-up-detection logic — mentioned to justify the flexible schema, but the actual sleep ingestion is a separate spec.
- Pagination beyond a single `?limit=` page — `GET /api/posts` returns up to 50 newest. Cursor pagination is in `services/posts.py`'s comment as a future addition.
- "Mark all as read" / unread state on the feed — read-only stream for v1.
- Email/push notifications for milestones — out of scope.
- Customizable milestone thresholds per user — fixed `[1000, 5000, 10000]` constant in the service.

## 9. Open questions resolved during brainstorming

| Question | Resolution |
|---|---|
| Feed page = stream or leaderboard? | Pure chronological stream. Leaderboard moves out. |
| Posts payload schema | `details jsonb` + `body text` + new specific types. |
| Multiple milestones from one write | Only the highest newly-crossed threshold. |
| DST handling for 6am cron | Fixed 11 UTC year-round; accept the 5am CT winter drift. |
| Idempotency for milestone re-fires | `details.date` + `details.threshold` + uniqueness-by-existing-row check. |
| Idempotency for the cron | `type='leaderboard_recap' AND details->>'date' = yesterday` lookup. |
| Recap post authorship (user_id NOT NULL) | Attributed to top-1 user; body/details make it clearly system content. |
