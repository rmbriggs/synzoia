# Sleep in the feed + profile pages — design

**Status**: Proposed (team review). Backend sleep table + `/api/sleep` endpoints already merged (PR #40). This adds the *presentation* layer: sleep activity in the global feed and on profile pages.

**Date**: 2026-05-29

## Goal

Make sleep data flow into the two surfaces that already show steps:

1. **The global feed** (`/feed`) — show a post each night someone logs sleep.
2. **Profile pages** (`/u/:username`) — show a user's sleep stats alongside their steps stats.

The `sleep` table is currently empty, and that is expected — no real sleep data exists until the iOS Shortcut starts POSTing it (Teammate A's area, out of scope here). This change builds the plumbing so sleep appears correctly the moment data arrives, and degrades to clean empty/zero states until then.

## Background: how steps reaches these surfaces today

- The **feed** renders rows from the `posts` table, not from `steps`/`sleep`. Steps appears in the feed because writing steps auto-creates a `steps_milestone` post (`services/steps.py::detect_and_insert_milestone`). **Writing sleep currently creates no post**, so sleep would never appear in the feed without a change.
- **Profile pages** read directly from the activity endpoints. `Profile.tsx`'s `SummaryPanel` calls `/api/steps/users/{u}/{daily,weekly,monthly,summary}` and renders cards. The matching `/api/sleep/users/{u}/...` endpoints already exist and return the same shape.

## Decisions

### D1 — A sleep write also creates one feed post (chosen: "post every night")

`POST /api/sleep` will, in the **same transaction** as the sleep-row insert, insert one `posts` row:

| Column | Value |
|---|---|
| `type` | `'sleep'` (already an allowed type in the `0007` CHECK + `PostType`) |
| `body` | pre-rendered text, e.g. `"slept 7h 32m"` |
| `details` | `{ "duration_min": 452, "night_of": "2026-05-28" }` (JSONB) |
| `timestamp` | the night's `wake_time` (morning sync → post lands near top of feed) |
| `user_id` / `username` | resolved server-side, same denormalization as other posts |

Rationale:
- **Same transaction** → a duplicate night (the `UNIQUE (user_id, night_of)` 409 path) or any failure rolls back the post too. No orphan posts, exactly one post per logged night.
- **`body` pre-rendered** mirrors `steps_milestone`, so even a generic renderer shows something sensible.
- **`details` carries structured data** so a dedicated component can render richly without re-fetching.
- **No migration** — `'sleep'` is already a valid post type.

Implementation note: mirror the `steps_milestone` insert (writes `body` + `details` directly) rather than `posts.create_post()` (which leaves them NULL). The insert lives in `services/sleep.py` and is called from the sleep route after `create_sleep`, inside the existing `begin()` transaction.

### D2 — Dedicated `SleepPost` feed component

Add `frontend/src/components/feed/SleepPost.tsx`, mirroring `MilestonePost.tsx`: `@user · slept 7h 32m · <time>`, with a subtle moon/😴 accent. Dispatch `type === 'sleep'` to it in **both** feed render sites:
- `frontend/src/pages/Feed.tsx` (global feed)
- the `FeedPanel` in `frontend/src/pages/Profile.tsx` (per-user feed)

A `'sleep'` post would already fall through to `GenericPost` (which renders `body`), so this is a polish/consistency step, not a correctness requirement.

### D3 — Sleep API wrapper

Add `frontend/src/api/sleep.ts`, a direct mirror of `steps.ts`: `getUserDaily / getUserWeekly / getUserMonthly / getUserSummary` (per-user is all the profile needs; globals can be added later if a Leaderboard tab happens). Response types mirror the sleep Pydantic schemas (totals are **minutes**).

### D4 — Profile layout: one Summary tab, two stacked sections (chosen)

Keep the existing `Summary` / `Feed` tabs unchanged. Inside `SummaryPanel`, render two labeled sections:

```
Summary tab:
  — STEPS —
  all-time / today / this-week / this-month   (existing cards, unchanged)
  — SLEEP —
  all-time / today / this-week / this-month   (new cards)
```

The sleep cards reuse the existing `StatCard` and `DailyBars` components; only the values and formatting differ. Sleep durations render as `7h 32m` (a `formatDuration(minutes)` helper). All-time/aggregate totals render in hours (e.g. `142h`).

Each sleep card handles its own pending/error/empty state the same way the steps cards do (they already tolerate "no data" → zeros / `—`).

## Components / files

**Backend**
- `backend/app/services/sleep.py` — add a helper to insert the `type='sleep'` post (body + details).
- `backend/app/routes/sleep.py` — call that helper inside the existing `create_sleep` transaction.
- `backend/tests/test_sleep_write.py` (or a new test file) — assert a sleep write creates the expected post; assert a duplicate-night write rolls back both rows.

**Frontend**
- `frontend/src/api/sleep.ts` — NEW. Mirror of `steps.ts` (per-user endpoints + types).
- `frontend/src/components/feed/SleepPost.tsx` — NEW. Mirror of `MilestonePost.tsx`.
- `frontend/src/lib/dates.ts` (or a small local helper) — `formatDuration(minutes) → "7h 32m"`.
- `frontend/src/pages/Feed.tsx` — dispatch `type === 'sleep'` → `SleepPost`.
- `frontend/src/pages/Profile.tsx` — dispatch `'sleep'` in `FeedPanel`; add a `SLEEP` section + sleep cards in `SummaryPanel`.
- `frontend/src/__tests__/Profile.test.tsx` + a feed test — cover the sleep section and `SleepPost`.

## Data flow

```
iOS Shortcut (future) ──POST /api/sleep──> create_sleep()  ┐ same txn
                                            + insert sleep post (type='sleep') ┘
                                                   │
        ┌──────────────────────────────────────────┴───────────────┐
        ▼                                                            ▼
  GET /api/posts (feed)                               GET /api/sleep/users/{u}/*
        │                                                            │
        ▼                                                            ▼
  Feed.tsx → SleepPost                          Profile.tsx SummaryPanel → SLEEP section
```

## Out of scope (possible follow-ups)

- Sleep tab on the global **Leaderboard** (would need the `/api/sleep/{daily,weekly}` global wrappers).
- Sleep **milestones / streaks** (e.g. "8h night", "5-night streak").
- The **iOS Shortcut** change to actually POST sleep — Teammate A.

## Testing strategy

- **Backend**: pytest — a sleep write inserts a matching `sleep` post (correct `type`, `body`, `details`, `timestamp`); a duplicate-night write (409) leaves **no** post (transaction rollback). Run the full suite (currently 105 passing) to confirm no regressions.
- **Frontend**: vitest — `SleepPost` renders body/time; `Profile` `SummaryPanel` shows the SLEEP section with formatted durations and a graceful empty state when the user has no sleep data; feed dispatch routes `'sleep'` to `SleepPost`.
