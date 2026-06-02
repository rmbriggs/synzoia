# Clearer feed — design

**Date:** 2026-06-02
**Status:** Approved (design)
**Scope:** frontend only (feed page + feed post components + date helpers). No backend or data changes.

## Goal

Make the Feed easier to understand at a glance. Today it's a flat,
newest-first stack of near-identical cards with no temporal structure and
no visual distinction between post types. This adds day grouping,
per-type visual cues, a cleaner fallback for body-less posts, and fixes a
misleading recap label.

## Context (current behavior)

- `Feed.tsx` renders `getFeed(50).posts` as a flat `space-y-4` stack,
  dispatching by `post.type` to `RecapPost` / `MilestonePost` /
  `SleepPost` / `GenericPost`.
- `FeedPost` shape: `{ id, user_id, username, type, timestamp, details, body }`.
  Types: `sleep | steps | workout | steps_milestone | leaderboard_recap`.
- The server returns posts **newest-first** (reverse chronological).
- Per-post date cue is only the small right-aligned `formatPostedAt`
  timestamp, which is inconsistent (today → time only; older → date).
- **Bodies already carry the numbers** for the main event types:
  - milestone: `body = "hit 10,000 steps"` (steps.py)
  - sleep: `body = "slept 7h 32m"` (sleep.py)
  - recap: renders from `details.top`; `body = "Yesterday's top 3"` (cron.py)
  - plain `steps` / `workout`: `body` may be null → GenericPost shows
    "posted (steps)".

## Design

### 1. Day delimiters

- **New pure helper** `frontend/src/lib/feedGroups.ts`:
  `groupPostsByDay(posts: FeedPost[], now?: Date): DayGroup[]` where
  `DayGroup = { key: string; label: string; posts: FeedPost[] }`.
  - `key` is the CT calendar day (`YYYY-MM-DD`) of `post.timestamp`.
  - Preserves input order; walks the list and starts a new group each
    time the CT day changes (server order is newest-first, so groups come
    out newest-day-first).
  - `label` comes from `formatDayHeader`.
  - Empty input → `[]`.
- **New date helper** `formatDayHeader(iso: string, now?: Date): string` in
  `frontend/src/lib/dates.ts`, reusing the existing `APP_TIMEZONE` /
  `CT_YMD` machinery (same Today/Yesterday logic as `formatPostedAt`):
  - same CT day as `now` → `"Today"`
  - CT day before `now` → `"Yesterday"`
  - otherwise → `"Tuesday, May 27"` (weekday, month day) via
    `toLocaleDateString('en-US', { timeZone, weekday:'long', month:'long', day:'numeric' })`.
- **`Feed.tsx`** maps over `groupPostsByDay(posts)` instead of the flat
  list. Each group renders a header (a `label-mono` text + a subtle
  divider, matching existing styling) followed by that group's posts in
  the existing `space-y-4` stack and the same per-type dispatch.

### 2. Distinct post types

- **New shared map** of type → `{ icon, label }` (icon = a lucide icon
  component; label = a short human string). Used for the non-recap types:
  - `sleep` → 🌙 "Sleep"
  - `steps_milestone` → 🏆 "Milestone"
  - `steps` → 👟 "Steps"
  - `workout` → 🏃 "Workout"
- `MilestonePost`, `SleepPost`, `GenericPost` render a leading type icon
  before `@username`. The icon carries an accessible label via
  `aria-label` + `title` (it is NOT icon-only for screen readers). Body
  text and right-aligned timestamp are unchanged.
- Lucide is already a dependency (`AppLayout` imports from `lucide-react`).
  Prefer lucide icons over literal emoji for visual consistency; emoji in
  the mock are illustrative.
- `RecapPost` keeps its distinct tinted card; no icon row needed (it's
  already visually unmistakable).

### 3. Cleaner fallback for body-less posts

- `GenericPost` fallback changes from `posted (${post.type})` to a
  per-type phrase: `steps` → "logged steps", `workout` → "logged a
  workout", anything else → "posted". Milestone and sleep already show
  their numbers and are untouched.

### 4. Accurate recap label

- `RecapPost` heading changes from the hardcoded "Yesterday's top 3" to
  **"Top 3 · {day}"**, where `{day}` is formatted from the recap's own
  `details.date` (the leaderboard day it ranks) using `formatDateMedium`
  (existing helper). Accurate regardless of the post's position in the
  feed. If `details.date` is missing, fall back to just "Top 3".

## Testing (TDD)

- `frontend/src/lib/__tests__/feedGroups.test.ts`:
  - posts spanning Today / Yesterday / an older day → three groups with
    the right labels, in newest-first order, posts intact.
  - all posts same day → one group.
  - empty input → `[]`.
- `frontend/src/lib/__tests__/dates.test.ts` (extend): `formatDayHeader`
  returns "Today" / "Yesterday" / "Weekday, Month Day" for a fixed `now`.
- `frontend/src/__tests__/Feed.test.tsx` (extend): feed with posts across
  two days renders both day headers; a sleep post exposes its accessible
  type label ("Sleep"); a recap renders "Top 3" with its `details.date`,
  not "Yesterday's top 3".

## Out of scope

- Backend / post-creation / data shape changes.
- Avatars, reactions, infinite scroll, or other feed features.
- Changing `getFeed`'s ordering or limit.
