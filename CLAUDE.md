# CLAUDE.md — synzoia team conventions

This file is loaded into every agent session for every teammate. It exists so Claude/Cursor produces consistent code across the three of us. The original design spec is `docs/superpowers/specs/2026-05-16-synzoia-design.md`; the **pivot spec** that describes the current shape is `docs/superpowers/specs/2026-05-23-backend-pivot-design.md` — read that one first.

## Project at a glance

- **What**: synzoia — a public-feed activity-tracking social app. Users ingest steps + sleep from an iOS Shortcut, everyone shares one universal real-time feed (posts, milestones, daily recaps), with per-user profiles and a leaderboard. (Pre-pivot this was a private-group sleep app with chat/reactions — that's what the 05-16 spec describes.)
- **Stack**: FastAPI (Python) + React/TS + Vite + Tailwind + Supabase Postgres/Realtime + Vercel hosting (FastAPI as Python serverless functions). Auth is custom bearer tokens minted at signup — NOT Supabase Auth.
- **Tier**: Gold. The gold pick-one is real-time (the live feed).
- **Due**: Day of lecture 10.2. ~3 weeks total.

## Repo layout

```
api/
  index.py                   # Vercel entrypoint — re-exports FastAPI app

backend/
  app/
    main.py                  # FastAPI entry, /api/* routes only (Vercel serves the SPA)
    auth.py                  # Bearer-token auth dependency (custom tokens in profiles)
    db.py                    # SQLAlchemy engine factory (NullPool; raw SQL, no ORM)
    routes/                  # Routers (one per resource: steps, sleep, posts, profiles, cron)
    services/                # Business logic (steps.py, sleep.py, sleep_sessions.py, posts.py, ...)
    schemas/                 # Pydantic request/response models
  migrations/                # Numbered .sql files (0001_*.sql, ...), applied via Supabase SQL editor
  tests/                     # pytest
  requirements.txt           # Source of truth for backend deps
  .env.example

frontend/
  src/
    main.tsx
    App.tsx                  # Router
    pages/                   # One per route
    components/              # Reusable UI
    hooks/                   # useCurrentUser, useTheme, etc.
    api/                     # fetch wrappers for /api/*
    lib/supabase.ts          # supabase-js client singleton
    __tests__/               # vitest
  package.json
  .env.example

docs/
  superpowers/specs/         # Design docs (the canonical one is in here)
  healthkit-research.md      # Bridge options for Teammate A

vercel.json                  # Two builds (static SPA + python fn) + rewrites
requirements.txt             # Defers to backend/requirements.txt via `-r`
.github/workflows/ci.yml     # Backend pytest; frontend typecheck + vitest + build. No lint step (yet). Deploy gate via branch protection
```

## Rules of the road

These are non-negotiable for keeping the team coherent. Push back on agents that deviate.

### Database

- **One source of truth for schema**: numbered `.sql` migrations in `backend/migrations/` (no Alembic). They're applied by hand via the Supabase SQL editor — so NEVER change the schema in the dashboard without committing a matching migration file, and write every migration to be idempotent (re-runnable). Migration 0010's header documents what happens when this rule is skipped.
- **Foreign keys everywhere** the schema calls for them. Real `ON DELETE` behavior (`CASCADE` for owned rows, `RESTRICT` for protected rows).
- **`CHECK` constraints + `NOT NULL` + `UNIQUE`** are enforced at the DB level, not just in Pydantic. The DB is the last line of defense.
- **`night_of` is a `date` anchored to Central Time** (`APP_TZ = America/Chicago`), computed at insert time. Never re-derive from `bedtime` in queries.
- **RLS policies** must exist for any table broadcast over Supabase Realtime (currently `posts` — see migrations 0006 + 0010). FastAPI connects with service-level credentials and bypasses RLS for writes.

### Backend (FastAPI)

- **`user_id` comes from the Bearer token (`require_user`), never from the request body.** Resolving identity from headers/body is the bug that ate week 2 of past projects.
- **Writes that touch a row by id carry an ownership clause in the query**: `WHERE id = :id AND user_id = :uid`, not a separate check. (Per Lecture 9.2 — the check lives IN the query.)
- **Raw parameterized SQL** via `text()` + bind params everywhere; there is no ORM layer. Identifiers (table/column names) are never built from request input.
- **Endpoint paths are plural nouns + ids**: `/api/posts/users/{username}`, not `/api/post/getByUser`.
- **Errors return `{error: {code, message}}`** with the right HTTP status. 401 unauthed, 403 forbidden, 404 nonexistent, 409 unique conflict, 422 validation.
- **No `print()` in checked-in code**. Use the `logging` module.

### Frontend (React)

- **React Query for all server data.** No raw `useEffect(fetch)`. Cache keys are stable and match the URL.
- **Single Supabase client instance** at `frontend/src/lib/supabase.ts`. Import it; never `new SupabaseClient()` inline.
- **Every fetch has loading + error states.** Skeletons + retry buttons, not blank screens.
- **Optimistic updates** for user-initiated writes. Rollback on error.
- **Routes are bookmarkable.** Refreshing keeps the user where they were. URL state for tab selection (`?tab=...`), not React state.
- **No CSS frameworks beyond Tailwind.** Don't import Material-UI, Chakra, etc. We're keeping the bundle thin.

### Realtime

- **Subscribe on mount, unsubscribe on unmount.** Leaks kill performance.
- **Filter subscriptions server-side** (Supabase Realtime filter clause), not in the callback. Don't pull every row and discard.
- **Optimistic UI + realtime echo**: when the user posts, show the post immediately; when the realtime echo arrives, reconcile by id and avoid duplicates.

### Tests

- **Backend**: pytest against per-test in-memory SQLite engines (each test file builds its own schema + seeds users; `db.get_engine` is monkeypatched). Fast, but `CHECK` constraints and RLS are Postgres-only and NOT exercised by tests — verify those by hand when a migration adds them.
- **Each owner writes tests for their slice.** The leaderboard owner writes leaderboard tests; the sleep owner writes sleep tests.
- **Cover happy path + at least one edge case per endpoint.** "Two users posting for the same night" and "re-posting the same window" are real edge cases worth testing.

### Git workflow

- **Commit often, push often.** Small, focused commits with present-tense messages.
- **Use feature branches** for anything that takes more than a few hours. Merge to `main` when tests pass.
- **CI gates merges to `main`.** No green, no merge.
- **No force-pushing to `main`.** Use force-with-lease on your own feature branches if you need to.

## "Push back if Claude tries to..."

Common agent failure modes worth catching in code review:

- Denormalizing usernames onto `posts` instead of joining `profiles`. (Users can rename; embedded names go stale. Yes, `posts.username` currently exists — that's the debt `refactor/posts-username-join` is paying down, don't add more.)
- Computing `night_of` from `bedtime` in every query instead of using the stored column.
- Adding indexes on every column "for performance." A few deliberate indexes, that's it.
- Storing auth tokens anywhere the frontend doesn't already put them. The user's token is shown once at signup for the iOS Shortcut; the web app itself doesn't hold it.
- Adding `useEffect` with `[]` deps for data fetching. Use React Query.
- Suggesting websockets or Socket.IO instead of Supabase Realtime. We have realtime; use it.
- Wrapping every endpoint in try/except that swallows errors. Let FastAPI's exception handlers do their job.
- Adding "validation" in three places (Pydantic, custom decorator, DB constraint). Constraints in the DB; Pydantic for shape; nothing custom.
- Configuring SQLAlchemy with a real connection pool. We deploy on Vercel serverless — use `NullPool` and connect via Supabase's pgbouncer pooler (port 6543).

## Pointers

- Original spec: `docs/superpowers/specs/2026-05-16-synzoia-design.md` (pre-pivot)
- Pivot spec (current shape): `docs/superpowers/specs/2026-05-23-backend-pivot-design.md`
- HealthKit bridge options for Teammate A: `docs/healthkit-research.md`
- Assignment PDF: not in repo (course material). Ask Micah if you need a section quoted.
