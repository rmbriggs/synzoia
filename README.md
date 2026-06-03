# synzoia

A private sleep- and steps-tracking social feed for our crew. An iOS Shortcut on each phone posts HealthKit data to the API; the web app turns it into a chronological feed with milestones, a daily recap post, and a rolling 30-day leaderboard. Built as the UATX Software Engineering final project, Spring 2026.

**Live URL**: https://synzoia.vercel.app
**GitHub**: https://github.com/rmbriggs/synzoia
**Tier**: Gold

## Team

- **Max Weinstein** (backend) — schema + migrations (sleep, crews, universal-feed pivot, steps), `POST /api/sleep` shaped to Angela's Shortcut payload, `POST /api/steps`, sleep sessionization (provisional/final, dedup), realtime-branch hardening (auth on per-user reads, locked `/api/db/dump`, RLS + publication codified as migration 0010).
- **Micah Briggs** (frontend + infra) — every page (Landing, Join, Feed with realtime push, Leaderboard, Profile, `/users`, DbExplorer), backend pieces around presentation (users endpoints, milestone post generation, daily-recap cron, grouped 4-4-4-4 token format, `/api/steps` reads), Vercel config + SPA fallback, RLS enablement (migration 0006), Central-Time anchoring throughout, design docs under `docs/superpowers/`, and the bulk of PR review/merges.
- **Angela** — built the iOS Shortcut that posts HealthKit sleep and step data to `/api/sleep` and `/api/steps`. The Shortcut lives on her phone, not in the repo, so she has no commits here; the contract surface only shows up as Max's "match API to Angela's Shortcut" commits.

## Nontrivial logic

**Bronze — sleep stage sessionization.** `ingest_payload` in `backend/app/services/sleep_sessions.py` parses the iOS Shortcut's raw HealthKit stage samples, splits them on >60-min gaps into night/nap sessions (classified by CT onset hour 20:00–05:00), computes per-stage metrics, marks each session provisional or final based on age since wake (<30 min = provisional), and overlap-dedups against existing rows inside a 30-min slop window. The design call: sessionize on the server, not in the Shortcut — Angela's payload is just raw samples, so the server can be re-run against the same data and produce the same sessions.

**Silver — rolling-30-day capped step leaderboard.** `get_global_ranking` in `backend/app/services/steps.py` (using `cap_and_sum` from `backend/app/services/windows.py`) sums each user's per-CT-day step totals over the rolling-30-day window from `rolling_bounds(as_of, 30)`, capping each individual day at `STEPS_DAILY_CAP` before summing. The design call: cap per day, not per window — one anomalous 80k-step day shouldn't carry a user for a month, but a consistent 15k/day user should still climb.

**Gold "pick one" — real-time push.** See below.

**Custom feature support — milestone + recap post generation.** `detect_and_insert_milestone` in `backend/app/services/steps.py` runs after every step write and inserts a single post for the highest newly-crossed 1k/5k/10k threshold for that CT day, checking existing `steps_milestone` posts to avoid re-firing. `write_daily_recap` in `backend/app/services/cron.py` (HTTP entry `daily_recap` in `backend/app/routes/cron.py`, scheduled `0 11 * * *` in `vercel.json`) computes yesterday CT's top-3 step posters, inserts one idempotent `leaderboard_recap` post attributed to the #1 user, and no-ops if a recap for that date already exists.

## Design decisions

**Universal feed table instead of per-type tables.** Sleep posts, step milestones, and recap posts all live in one `posts` table with a `type` discriminator and a JSON `details` blob. Adding a new post type is a new `type` value plus a renderer in the feed — no migration, no new endpoint. Migration 0003 was the pivot from a `sleep_posts`-only world to this one.

**Bearer-token API-key auth, not Supabase Auth.** The iOS Shortcut needs to post from a Siri command, where browser-based OAuth flows are awkward. So `/api/sleep` and `/api/steps` take an opaque token in `Authorization: Bearer <token>` and `backend/app/auth.py`'s `require_user` looks it up in `profiles.token`. The web UI tracks the current user as a plain localStorage username pointer (`frontend/src/hooks/useCurrentUser.ts`) — convenient for the demo, not real auth. A full Supabase Auth path was built on a separate branch but wasn't merged before the demo deadline; we left the shipped model honest rather than half-merging it.

**Central Time everywhere, not UTC.** Day boundaries (`night_of`, CT-day step buckets, "yesterday" for the recap) are all anchored to CT because every member of the crew is in Texas. UTC days would make 11pm posts and 1am posts look like different days for the same night, which breaks the leaderboard.

**`NullPool` + Supabase pgbouncer.** Vercel serverless functions die between requests, so a real connection pool just leaks. We use `NullPool` and connect through Supabase's pgbouncer pooler on port 6543. This is in CLAUDE.md as a rule because we caught one PR trying to add a real pool.

## Where Claude helped, and where we pushed back

Claude was great at the mechanical middle: writing migrations from a schema sketch, generating React Query hooks that matched the API surface, and producing the per-stage sleep metrics math from a verbal description. It was also good at catching the small stuff — missing `NOT NULL`s, forgetting to invalidate the right query key after a mutation, RLS policies we'd forgotten to write. Where we pushed back: it kept trying to denormalize `display_name` onto `posts` "for performance," kept reaching for `useEffect(fetch)` instead of React Query, suggested Socket.IO once even though we already had Supabase Realtime, and at one point wanted to wrap every endpoint in a try/except that swallowed `IntegrityError`. CLAUDE.md's "Push back if Claude tries to..." section is the running list of things we caught more than once.

## Run locally

```bash
# clone + install
git clone https://github.com/rmbriggs/synzoia.git
cd synzoia
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
(cd frontend && npm install)

# env (backend/.env)
DATABASE_URL=postgresql+psycopg://...:6543/postgres  # Supabase pooler
CRON_SECRET=...                                      # for /api/cron/daily-recap
STEPS_DAILY_CAP=25000

# env (frontend/.env)
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=...
VITE_API_BASE=http://localhost:8000

# migrate: paste each backend/migrations/*.sql file into the Supabase
# SQL Editor in numeric order (0001 → 0011). The files are idempotent —
# safe to re-run. We use raw SQL rather than Alembic so the migration
# history is also a readable spec.

# run
(cd backend && uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev)

# tests
(cd backend && pytest)
(cd frontend && npm test)
```

## Gold features

**Pick-one: real-time push updates via Supabase Realtime.** `frontend/src/pages/Feed.tsx`'s `Feed` component opens `supabase.channel('posts-feed-realtime')` on mount, listens for `INSERT` events on `public.posts`, and invalidates the `['posts']` React Query keys when an event arrives so the feed refetches. The channel is removed on unmount. RLS + publication for the `posts` table are codified in migration 0010 so this works in production, not just locally.

**Custom 1 — auto-generated activity feed.** The feed isn't just user-authored posts. `detect_and_insert_milestone` in `backend/app/services/steps.py` writes a `steps_milestone` post the first time a user crosses 1k / 5k / 10k steps on a given CT day, and `write_daily_recap` in `backend/app/services/cron.py` runs at 11:00 UTC and writes a `leaderboard_recap` post summarizing yesterday's top-3 step posters. Both flow through the same `posts` table the realtime channel watches, so generated posts push to every open client the same way user-authored ones do.

**Custom 2 — hover-intent prefetch on the Users page.** `UserRow` in `frontend/src/pages/Users.tsx` arms a 100 ms `setTimeout` on `onMouseEnter` (`HOVER_PREFETCH_DELAY_MS = 100`) that fires `queryClient.prefetchQuery` for the eight Summary-tab queries returned by `userSummaryQueries(...)`. Mouseleave/unmount cancels the timer; keyboard `onFocus` skips the delay and prefetches immediately. The result is that clicking from the user index into a profile is effectively instant — the Summary tab's data is already in the cache by the time the route mounts.
