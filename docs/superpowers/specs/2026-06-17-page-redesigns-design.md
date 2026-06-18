# SP3 — Page Redesigns Design

**Date:** 2026-06-17
**Status:** Approved (design); implementation plan pending
**Owner:** rmbriggs (Micah)

## Context

Third of four sub-projects applying the "Santa Cruz coastal" design from
`SamM-UATX/synzoia-mockups` to the real app. SP1 (repo + hosting migration) is done.
SP2 (coastal theme foundation: palette, fonts, primitives) is built on branch
`worktree-sp2-coastal-theme` (PR #2, previewed, not yet merged). SP3 stacks on SP2 so
the coastal theme is present. See [[project_synzoia_coastal_redesign]].

- SP1 — repo + hosting migration. DONE.
- SP2 — coastal theme foundation. Built (preview).
- **SP3 — page redesigns (this doc).** Rebuild the pages in the coastal language.
- SP4 — Messages feature (net-new). Later.

## Guiding principle: real data only

The mockups depict many features with **no backend** (heart rate, calories, meals,
photos, avatars-as-uploads, likes/comments/shares, followers/following, badges,
weather, trending hashtags, suggested users). The real synzoia is steps + sleep, a
public feed, a leaderboard, and profiles, with no auth and no social layer.

SP3 reproduces the coastal **look** and as much of the mockup **layout** as the real
data supports. **Every element shown is backed by an existing API.** Mockup sections
with no data are omitted, not faked. Two no-backend "cheap wins" are allowed:

- **Generated avatars** — a deterministic avatar (initials on a coastal gradient
  derived from a hash of the username). Real identity, no uploads, no backend.
- **Day streak** — computed client-side from the daily-steps series the profile
  already fetches. Definition: the number of consecutive days ending today (in
  `America/Chicago`) that have a recorded steps entry > 0. No backend.

SP3 is **frontend only**: no backend, API, Supabase, or new-endpoint changes.

## Current state (verified 2026-06-17)

- Pages: `frontend/src/pages/` — `Landing.tsx` (exists but NOT routed), `Feed.tsx`,
  `Profile.tsx`, `Leaderboard.tsx`, `Users.tsx`, `Join.tsx`, `StyleGuide.tsx`,
  `DbExplorer.tsx`.
- Router `frontend/src/App.tsx`: `/` hard-redirects to `/feed`; app pages render inside
  `AppLayout`; `Landing` is not imported.
- Data layer: React Query hooks in `frontend/src/api/` wrap `/api/*`. Key endpoints:
  `/api/posts` (feed), `/api/posts/users/{username}` (user feed), `/api/profiles`
  (list: `{username, join_date, total_steps_all_time}`), `/api/steps/{daily,weekly,
  monthly,summary,ranking}`, `/api/sleep/{daily,weekly,monthly,summary,ranking}`,
  per-user summary queries in `userSummaryQueries.ts`.
- `/api/steps/summary` returns `{total_users, total_steps_all_time, today_leader,
  this_week_leader, best_day_ever}`; `/api/sleep/summary` is the sleep analogue.
- Feed posts: `{id, user_id, username, type, timestamp, details, body}`; types include
  generic, milestone, leaderboard_recap, sleep. Components in `components/feed/`.
- Profile uses 8 React Query calls (`userSummaryQueries.ts`): steps + sleep summary /
  daily / weekly / monthly.
- Every fetch already has loading + error states (project convention); SP3 preserves
  them. No `avatar_url`, photos, HR, calories, social, badges, or streak fields exist
  in any response.

## Routing change

`/` renders the new `Landing` (front door). The feed stays at `/feed` and the rest of
the app is unchanged. `Landing` gets imported into `App.tsx`; the `/` redirect is
removed and replaced with `<Route path="/" element={<Landing />} />`. The landing has
its own marketing nav (not the `AppLayout` shell) with a CTA into `/feed`.

## Shared component (built first)

**`UserAvatar`** (`frontend/src/components/ui/UserAvatar.tsx`): given a `username` (and
optional size), renders initials over a deterministic coastal gradient derived from a
hash of the username, using the existing `avatar.tsx` primitive. Used by Feed, Profile,
Leaderboard, and Users. No network, no props beyond `username`/`size`/`className`.

## Per-page design (build order)

### 1. Landing (`/`) — large, mockup-backed (`landing.html`)

Coastal marketing page, real stats only. Sections:
- Sticky marketing nav: serif-italic logo (teal `z`), anchor links (Features, How it
  works), and a primary "Open the feed" CTA to `/feed`.
- Hero: coastal headline + subcopy + a **live stat bar** from real aggregates —
  `/api/steps/summary` (`total_users` as "walkers", `total_steps_all_time`,
  `this_week_leader`, `best_day_ever`) and `/api/sleep/summary` (a real sleep aggregate).
  Loading + error states required.
- Features grid: cards for what the app actually does — steps + sleep ingestion via the
  iOS Shortcut, the universal public feed, the leaderboard, per-user profiles.
- "How it works": 3 steps (join and get a token, paste it into the iOS Shortcut, your
  steps + sleep post to the shared feed).
- CTA band (dark fern) with a button to `/feed`.
- Footer (coastal).
- **Omits:** coastal photo strip, testimonials, health-ring demo, dark app-screen
  preview band, meal photos (no image data or HR/calorie data).

### 2. Feed (`/feed`) — large, mockup-backed (`feed.html`)

Keep the single-column feed inside `AppLayout`; redesign the post cards to coastal.
- Post cards: `UserAvatar` + username (links to profile) + relative timestamp + body,
  with type-specific accent and an optional metric chip derived from the post's real
  `details` (e.g. sleep duration for sleep posts, leader for `leaderboard_recap`).
  Preserve the existing per-type components (`GenericPost`, `MilestonePost`,
  `RecapPost`, `SleepPost`) and day grouping + realtime subscription.
- Optional cheap win: a desktop-only right rail showing a **mini-leaderboard** (top 3
  today) from the existing `/api/steps/daily` data. Hidden on mobile.
- **Omits:** photo attachments, likes/comments/share/DM, global search, meal/HR type
  filters, weather/suggested-users/trending-hashtags sidebars.

### 3. Profile (`/u/:username`) — large, mockup-backed (`profile.html`)

Coastal profile, real data only.
- Header: `UserAvatar` over a coastal gradient banner (no photo), `@username`, join
  date, all-time steps, and the computed **day streak**.
- Stats row: real values only — 30-day step score + rank, 30-day sleep score + rank,
  best day, best night, all-time steps. (No followers/following.)
- Body: keep the existing Summary tab (steps + sleep cards + `RangeTrendCard` trend
  charts) and the user-posts Feed tab, both restyled into coastal cards. Steps and
  sleep may be shown as two ring-style gauges (only the two metrics that exist).
- Reuse the existing 8 React Query sources; restyle their presentation only.
- **Omits:** HR/calorie rings, Follow/Message buttons, followers/following counts,
  photo grid, badges, online dot.

### 4. Leaderboard (`/leaderboard`) — small-medium, no mockup

Coastal restyle of the existing ranked list: top-3 medal coloring (gold/silver/bronze),
`UserAvatar` per row, coastal card surfaces. Keep the Today / Last-30-days tabs
(`/api/steps/daily`, `/api/steps/ranking`). Optional cheap win: a **sleep leaderboard
tab** using the existing `/api/sleep/ranking`. Applies the SP2 design language; no
mockup to match.

### 5. Users (`/users`) — small, no mockup

Coastal restyle: render `UserAvatar` + `@username` + `total_steps_all_time` per row
(the steps total is already in the `/api/profiles` response but not currently shown).
Keep the existing hover-prefetch behavior. Coastal card/list styling.

## Scope / non-goals

- Frontend only. No backend, API, Supabase, or new-endpoint changes.
- No social features, photos, HR, calories, meals, badges, weather, or hashtags.
- No changes to data hooks' signatures or to component public contracts beyond what a
  restyle needs; preserve existing loading/error/empty states.
- Messages page/feature is SP4.

## Verification

- Per page: `npm run lint`, `npm run typecheck`, `npx vitest run`, `npm run build` pass.
- Existing data hooks and their tests unchanged; existing component tests still pass.
- Each page keeps loading + error + empty states (skeletons/retry, not blank screens).
- Visual review on the Vercel preview as each page ships (the branch stacks on SP2, so
  the preview shows the coastal theme + redesigned pages together).

## Decomposition

One SP3 spec (this) and one implementation plan with **per-page tasks**: `UserAvatar`
first, then Landing, Feed, Profile, Leaderboard, Users in order. Each task is
independently testable, reviewable, and shippable to the preview. All work lands on
`worktree-sp3-page-redesigns` (stacked on SP2).

## Success criteria

- `/` renders the coastal Landing with a real live stat bar and a CTA into the app.
- Feed, Profile, Leaderboard, Users render in the coastal language with `UserAvatar`s,
  driven entirely by real data; no faked metrics.
- All omitted (data-less) mockup sections are absent, not stubbed with fake data.
- CI green; preview shows the redesigned pages on the coastal theme; existing tests pass.
