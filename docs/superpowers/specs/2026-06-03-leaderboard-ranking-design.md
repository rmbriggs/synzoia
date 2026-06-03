# Better global ranking: 30-day capped score — design

**Date:** 2026-06-03
**Status:** Draft (in review)
**Scope:** backend ranking computation (steps + sleep) + frontend (profile rank/score cards + leaderboard). Builds on the rolling-windows work (`rolling_bounds`). No DB/migration changes.

## Goal

Replace the **all-time-total** basis of the global ranking with a metric that rewards recent, consistent activity and is fair across tenure. Surface it on the profile rank card and the leaderboard, for both steps and sleep.

## Motivation

All-time total just rewards whoever's been around longest or logged the most days — not who's doing well. After researching Strava (weekly leaderboard, resets, ranked by total) and Apple Fitness / Fitbit (capped daily points so consistency beats one big day), and the owner's three constraints:

1. A top user who takes a week off should **slide a few spots (to ~#10–15), not collapse to last**.
2. A new user with great numbers should **climb steadily but not hit #1 on day 3** — and not be locked out for a month either.
3. The algorithm must be **simple, explainable, and hard to game**.

## The metric

For each user:

```
score = Σ over the last 30 CT days of  min(day_total, DAILY_CAP)
```

- Un-logged days contribute 0.
- Rank users by `score` descending; ties broken by username (stable).
- **Steps:** `DAILY_CAP = 20_000` steps/day (clips only anomalies, rewards legit big days); window = `rolling_bounds(today, 30)` = `[today-29, today]`.
- **Sleep:** `DAILY_CAP = 540` minutes (9h)/night; window = `rolling_bounds(lastNight, 30)` = `[today-30, today-1]` (sleep is anchored to last night, consistent with the rest of the app — today's night isn't slept yet).

Each part of this formula traces to a specific owner goal — see **Owner's reasoning** below: the **30-day window** + **daily cap** give graceful decay on a week off, the **sum** (not average) gives the new-user ramp, and the **one-line rule** keeps it ungameable.

The caps are tunable constants — set near the top of a "normal great" day so strong users bunch (that bunching is what makes a week off cost real places).

## Backend

A shared idea, applied to both services (`services/steps.py`, `services/sleep.py`):

- New helper `_capped_window_scores(conn, start, end, cap) -> dict[user_id, int]`: pull per-(user, day) totals in `[start, end]` (steps: per-CT-day max, as the existing daily aggregation already does; sleep: per-`night_of` duration), cap each day at `cap`, sum per user. Reuses the existing `_daily_totals_in_range` / nightly-rows helpers.
- A ranking function `get_global_ranking(conn, as_of, cap) -> RankingResponse` returning the ranked leaderboard (username, rank, score) for the window.
- `get_user_summary` changes: `rank_all_time` (computed from all-time totals) → **`rank`** computed from `_capped_window_scores` for the user's window; also returns the user's **`score`** (their 30-day capped sum) so the profile can show it.
- Caps live as module constants: `STEPS_DAILY_CAP = 20_000` (steps.py), `SLEEP_DAILY_CAP_MIN = 540` (sleep.py).

Schema: `UserSummaryResponse` renames `rank_all_time` → `rank` and adds `score: int` (the capped 30-day sum). The leaderboard ranking response reuses the existing leaderboard entry shape (`rank, username, total`) with `total` now meaning the capped 30-day score.

## Frontend

- **Profile rank card** (both strips): label "All-time rank" → **"Rank"** (or "30-day rank"); value is the new window rank.
- **All-time steps/sleep card → "30-day score"**: show the user's capped 30-day `score` (the number they're ranked by), so the card and the rank are paired and coherent. (steps: formatted number; sleep: formatted hours.)
- **Days active / Nights logged card:** **dropped.** Each strip becomes a tight **3 cards: 30-day score · Rank · Best day/night.**
- **Leaderboard page:** the main board ranks by the 30-day capped score (label e.g. "Last 30 days"); keep the existing **"Today"** snapshot tab. Bars/standings reuse existing components.

## Testing (TDD)

- Backend: `_capped_window_scores` caps per day and sums (a 30k day counts as `cap`); ranking orders by score; the three scenarios as unit tests — (a) a user with a week of zeros inside the window still outranks low-volume users; (b) a 3-day-old user with high dailies ranks below a 30-day-full user; (c) capping changes the order vs an uncapped sum. Window bounds (`[today-29, today]` steps; `[today-30, today-1]` sleep).
- Frontend: rank/score card render; leaderboard ranks by the new metric; "Today" tab still present.

## Owner's reasoning (why the calculation is shaped this way)

The metric was derived directly from three goals the owner set, for a hypothetical ~100-user app. Each goal maps to a specific part of the formula — recording this so future changes don't quietly break an intended property:

1. **"If the world #1 takes a week off, I want him to fall a couple of spots (maybe to 10 or 15), but not to #100."** → A **30-day window** (not 7-day) means a week off removes only ~1/4 of the score, so it's a slide, not a collapse. The **daily cap** bunches strong users together near `cap × 30`, which is what makes that slide cross ~10–15 real places instead of zero. (A 7-day window would zero him out; an uncapped or all-time metric would barely move him.)
2. **"A new user with a high daily average shouldn't be world #1 on day 3, but I don't want him locked out until he's been on the app a month."** → Ranking by a **sum** (not an average) means a 3-day-old user has only banked 3 days and can't out-total a 30-day-full user — yet every logged day adds to the score, so he climbs steadily from day one and reaches full strength at 30 days. No min-days gate, no month-long lockout.
3. **"Don't make the algorithm too complicated — that makes it easier to game and harder to understand why you're not improving."** → The rule is one sentence ("most steps/sleep over the last 30 days, each day capped"). The cap removes the single-big-day exploit, and "just keep showing up" is the only lever — so it's both hard to game and easy to reason about.

## Resolved decisions

1. **4th card:** the days-active / nights-logged card is **dropped** → 3-card strip (30-day score · Rank · Best day/night).
2. **Caps:** **steps 20,000/day** (higher — clip only anomalies, reward legit big days), **sleep 9h (540 min)/night** (lower).
3. **`rank_all_time` field:** rename to **`rank`** and add a **`score`** field (the capped 30-day sum) to `UserSummaryResponse`.

## Out of scope

- DB schema / migrations.
- The cron recap (daily-only).
- Per-window leaderboards beyond the 30-day board + Today tab (e.g. weekly/monthly leaderboard tabs).
