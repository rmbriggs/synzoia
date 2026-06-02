# Feed as the default view (hide Landing) — design

**Date:** 2026-06-02
**Status:** Approved (design)
**Scope:** frontend routing only

## Goal

Make the Feed the app's default view. Opening the app at `/` should land
the user on the Feed instead of the marketing Landing page. The Landing
page is hidden for now — kept in the repo, but not reachable by any URL.
This is a temporary, easily-reversed change, not a deletion.

## Context

- The app has **no auth** (`useCurrentUser` is a localStorage convenience;
  `getFeed` is fully public). There is no logged-out state to special-case,
  so the Feed is safe to show as the default for everyone.
- Current routing (`frontend/src/App.tsx`):
  - `/` → `Landing` (standalone, no AppLayout chrome)
  - `/join`, `/style-guide` → standalone
  - `/feed`, `/users`, `/leaderboard`, `/u/:username`, `/db` → inside `AppLayout`
- The whole nav, the logo link, and `AppLayout` already point at `/feed`,
  so `/feed` is already the canonical feed URL.
- `Landing` is imported **only** in `App.tsx`; removing it there fully
  unroutes the page.

## Design

A single change in `frontend/src/App.tsx`:

1. Replace the index route with a redirect to the canonical feed URL:
   ```tsx
   <Route path="/" element={<Navigate to="/feed" replace />} />
   ```
   - `Navigate` is imported from `react-router-dom`.
   - `replace` avoids leaving a dead `/` entry in history, so the browser
     back button behaves naturally.
2. Remove the `import Landing from '@/pages/Landing'` line and its route.

`Landing.tsx` stays on disk, untouched. Everything else
(`/feed`, `/join`, `/users`, `/leaderboard`, `/u/:username`, `/db`,
`/style-guide`, the nav, the logo) is unchanged.

### Why redirect rather than render `<Feed/>` at `/`

Redirecting to `/feed` keeps one canonical feed route. The whole nav and
`AppLayout` already link to `/feed`, and the Feed keeps its AppLayout
chrome (header + bottom nav). There's no duplicate route to keep in sync,
and un-hiding Landing later is a one-line revert.

## Testing

Per the repo's TDD convention, update `frontend/src/__tests__/smoke.test.tsx`:

- The existing test `renders the landing page at "/" when logged out`
  (asserts `/` contains the Landing headline "More than a step counter.")
  is flipped to assert the **new** behavior: `/` now renders the Feed.
  Assert the page contains the Feed's unique copy
  ("Recent milestones and recaps.") and does **not** contain the Landing
  headline. This test fails against the current router (TDD red), then
  passes after the route change (green).
- The existing route-loop assertion (`renders an <h1> at /`) is unchanged
  and still passes: `/` redirects to `/feed`, and the Feed renders an
  `<h1>` via `PageHeader title="Feed"`.

## Out of scope

- Landing page content, the `/join` onboarding flow, and all other routes.
- Any deletion of files.
- Auth / logged-out handling (there is none to add).
