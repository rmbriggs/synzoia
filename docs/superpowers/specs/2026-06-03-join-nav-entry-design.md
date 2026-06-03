# Join nav entry — design

**Date:** 2026-06-03
**Status:** Draft (in review)
**Scope:** frontend only — `AppLayout`. No backend/DB/route changes (the `/join` route + page already exist).

## Goal

There is a working `/join` onboarding page, but nothing in the app links to it — a new user who lands on `/feed` (the default view) can't discover it. Add an **always-visible "Join" entry** to the app nav, pointing at `/join`.

## Context

- `frontend/src/components/layout/AppLayout.tsx` wraps the app pages. It has:
  - a **desktop header nav** (`hidden sm:flex`): `Feed · Leaderboard · Users · Database`, followed by a profile icon (`CircleUser` → `profileTarget`) and `ThemeToggle`.
  - a **mobile bottom nav** (`sm:hidden`): `Feed · Leaderboard · Users · Database · Me`, each an icon+label `BottomNavItem`.
- `/join` is routed in `App.tsx` *outside* the `AppLayout` group, so the Join page renders standalone (no app chrome) — fine; the nav entry just navigates there.

## Design

Always-visible (regardless of `currentUser`):

1. **Header (desktop):** add a `Join` `NavLink` to `/join` after "Database", using the existing `topNavClass` so it matches the nav, with `text-primary` added as a light CTA emphasis (it's the one action among informational links).
2. **Bottom nav (mobile):** add a `Join` `BottomNavItem` (lucide `UserPlus` icon + label "Join") to `/join`, placed before the "Me" item.
3. The profile icon / "Me" entry is unchanged.

No conditional on `currentUser` — the link is always shown (chosen over a contextual swap for simplicity).

## Testing (TDD)

`frontend/src/__tests__/AppLayout.test.tsx`:
- The header renders a "Join" link with `href="/join"`.
- The bottom nav renders a "Join" entry linking to `/join`.

## Out of scope

- The `/join` page itself and the onboarding flow (already built).
- Auth/contextual behavior (the app has no auth; link is unconditional).
