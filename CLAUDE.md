# CLAUDE.md — synzoia team conventions

This file is loaded into every agent session for every teammate. It exists so Claude/Cursor produces consistent code across the three of us. The full design spec is at `docs/superpowers/specs/2026-05-16-synzoia-design.md` — read it first.

## Project at a glance

- **What**: synzoia — a private-group sleep-tracking social app. Crews post nightly sleep, see each other's posts in a real-time feed, react, chat, and watch a rolling leaderboard.
- **Stack**: FastAPI (Python) + React/TS + Vite + Tailwind + Supabase Postgres/Auth/Realtime + Railway hosting.
- **Tier**: Gold. The gold pick-one is real-time; custom features are group chat and reactions.
- **Due**: Day of lecture 10.2. ~3 weeks total.

## Repo layout

```
backend/
  app/
    main.py                  # FastAPI entry, mounts /api and serves dist/
    auth.py                  # Supabase JWT verification dependency
    db.py                    # SQLAlchemy session / engine
    models/                  # ORM models (one file per table family)
    routes/                  # Routers (one per resource: groups, sleep, chat, ...)
    services/                # Business logic (leaderboard.py, streaks.py)
    schemas/                 # Pydantic request/response models
  migrations/                # Alembic
  tests/                     # pytest
  requirements.txt
  .env.example

frontend/
  src/
    main.tsx
    App.tsx                  # Router
    pages/                   # One per route
    components/              # Reusable UI
    hooks/                   # useAuthSession, useGroupRealtime, etc.
    api/                     # fetch wrappers for /api/*
    lib/supabase.ts          # supabase-js client singleton
    __tests__/               # vitest
  package.json
  .env.example

docs/
  superpowers/specs/         # Design docs (the canonical one is in here)
  healthkit-research.md      # Bridge options for Teammate A

.github/workflows/ci.yml     # Lint + typecheck + tests + deploy gate
```

## Rules of the road

These are non-negotiable for keeping the team coherent. Push back on agents that deviate.

### Database

- **One source of truth for schema**: Alembic migrations in `backend/migrations/`. Never edit the DB by hand in production; write a migration.
- **Foreign keys everywhere** the schema calls for them. Real `ON DELETE` behavior (`CASCADE` for owned rows, `RESTRICT` for protected rows).
- **`CHECK` constraints + `NOT NULL` + `UNIQUE`** are enforced at the DB level, not just in Pydantic. The DB is the last line of defense.
- **`night_of` is a `date` in the poster's timezone**, computed at insert time. Never re-derive from `bedtime` in queries.
- **RLS policies** must exist for any table broadcast over Supabase Realtime (`sleep_posts`, `reactions`, `messages`). FastAPI uses the service role key and bypasses RLS for writes.

### Backend (FastAPI)

- **`user_id` comes from the JWT, never from the request body.** Resolving identity from headers/body is the bug that ate week 2 of past projects.
- **Group-scoped endpoints check `memberships`** before reading or writing. Return 403 if the caller isn't in the group.
- **Use SQLAlchemy ORM** for normal queries; drop to raw SQL only for the leaderboard aggregation (it's complex enough that SQL is clearer than ORM gymnastics).
- **Endpoint paths are plural nouns + ids**: `/api/groups/{id}/messages`, not `/api/group/getMessages`.
- **Errors return `{error: {code, message}}`** with the right HTTP status. 401 unauthed, 403 forbidden, 404 nonexistent, 409 unique conflict, 422 validation.
- **No `print()` in checked-in code**. Use the `logging` module.

### Frontend (React)

- **React Query for all server data.** No raw `useEffect(fetch)`. Cache keys are stable and match the URL.
- **Single Supabase client instance** at `frontend/src/lib/supabase.ts`. Import it; never `new SupabaseClient()` inline.
- **Every fetch has loading + error states.** Skeletons + retry buttons, not blank screens.
- **Optimistic updates** for posting sleep, reacting, sending chat. Rollback on error.
- **Routes are bookmarkable.** Refreshing keeps the user where they were. URL state for tab selection (`?tab=chat`), not React state.
- **No CSS frameworks beyond Tailwind.** Don't import Material-UI, Chakra, etc. We're keeping the bundle thin.

### Realtime

- **Subscribe on mount, unsubscribe on unmount.** Leaks kill performance.
- **Filter subscriptions server-side** (Supabase Realtime filter clause), not in the callback. Don't pull every row and discard.
- **Optimistic UI + realtime echo**: when the user posts, show the post immediately; when the realtime echo arrives, reconcile by id and avoid duplicates.

### Tests

- **Backend**: pytest, transaction-per-test rollback, real Postgres in CI (service container).
- **Each owner writes tests for their slice.** The leaderboard owner writes leaderboard tests; the streaks owner writes streak tests.
- **Cover happy path + at least one edge case per endpoint.** "Two users posting at the same night for the same group" is a real edge case worth testing.

### Git workflow

- **Commit often, push often.** Small, focused commits with present-tense messages.
- **Use feature branches** for anything that takes more than a few hours. Merge to `main` when tests pass.
- **CI gates merges to `main`.** No green, no merge.
- **No force-pushing to `main`.** Use force-with-lease on your own feature branches if you need to.

## "Push back if Claude tries to..."

Common agent failure modes worth catching in code review:

- Denormalizing `display_name` onto `sleep_posts` instead of joining `profiles`. (Users can rename themselves; embedded names go stale.)
- Computing `night_of` from `bedtime` in every query instead of using the stored column.
- Adding indexes on every column "for performance." Three deliberate indexes, that's it.
- Storing JWTs in `localStorage` directly. Use `supabase-js`'s built-in session storage.
- Adding `useEffect` with `[]` deps for data fetching. Use React Query.
- Suggesting websockets or Socket.IO instead of Supabase Realtime. We have realtime; use it.
- Wrapping every endpoint in try/except that swallows errors. Let FastAPI's exception handlers do their job.
- Adding "validation" in three places (Pydantic, custom decorator, DB constraint). Constraints in the DB; Pydantic for shape; nothing custom.

## Pointers

- Full spec: `docs/superpowers/specs/2026-05-16-synzoia-design.md`
- HealthKit bridge options for Teammate A: `docs/healthkit-research.md`
- Assignment PDF: not in repo (course material). Ask Micah if you need a section quoted.
