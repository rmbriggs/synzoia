# Congratulatory leaderboard recap — design

**Date:** 2026-06-02
**Status:** Approved (design)
**Scope:** frontend only — `RecapPost` component. No backend/data changes.

## Goal

Make the daily steps leaderboard recap post feel celebratory rather than
a dry ranked list. "Podium with medals" treatment.

## Context

- `RecapPost` (`frontend/src/components/feed/RecapPost.tsx`) renders the
  `leaderboard_recap` feed card from `post.details`:
  `{ date: string; top: { username: string; total: number }[] }`.
- The feed builds the recap card itself and ignores the backend `body`
  ("Yesterday's top 3"), so this is purely presentational — frontend-only.
- Current heading (after the feed-clarity change):
  `Top 3 · {formatDateMedium(details.date)}`, followed by an `<ol>` whose
  rows show a `#{i+1}` rank label, the `@username` link, and the total.
- `details.top` is capped at 3 entries server-side (cron ranks `[:3]`).

## Design

Two changes inside `RecapPost`, nothing else touched:

1. **Celebratory heading.** Replace `Top 3 · {date}` with
   `🏆 Congrats to the top 3 · {date}`, keeping the existing
   `· {formatDateMedium(rankedDate)}` date format for consistency. The 🏆
   is wrapped in `<span aria-hidden="true">` (decorative — "Congrats to
   the top 3" carries the meaning), matching how the codebase treats
   decorative emoji. When `details.date` is missing, the heading is
   `🏆 Congrats to the top 3` (no date).

2. **Medals on the podium.** Replace the `#{i+1}` rank label with a medal
   for the top three: index 0 → 🥇, 1 → 🥈, 2 → 🥉, with a defensive
   `#{i+1}` fallback for any index beyond 2 (won't occur given the
   server-side top-3 cap). Each medal renders in a `<span>` with
   `role="img"` and `aria-label` of `"1st place"` / `"2nd place"` /
   `"3rd place"`, so assistive tech announces the rank rather than an
   ambiguous emoji name. The `@username` links, right-aligned totals, and
   the tinted `bg-accent/10` card are unchanged.

## Testing (TDD)

In `frontend/src/__tests__/Feed.test.tsx`:

- Update the two existing recap assertions (currently
  `getByText('Top 3 · May 23, 2026')`) to match the new heading via a
  regex, e.g. `getByText(/Congrats to the top 3 · May 23, 2026/)` — robust
  against the leading emoji.
- Add assertions to the "renders a recap card with the top-3 list" test:
  🥇 / 🥈 / 🥉 are present (e.g. `getByText('🥇')`) and the old `#1` label
  is gone (`queryByText('#1')` is null).

## Out of scope

- Backend / cron / `details` shape, the recap `body` text.
- Other post types, the day-grouping, or any non-recap feed behavior.
