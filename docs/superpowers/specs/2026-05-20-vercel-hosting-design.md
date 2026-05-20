# synzoia — Vercel hosting design

**Date**: 2026-05-20
**Status**: Supersedes Railway hosting in [`2026-05-16-synzoia-design.md`](./2026-05-16-synzoia-design.md) §3 and §8
**Owner**: Micah

---

## 1. Why this exists

The original spec assumed Railway: one long-lived service running FastAPI that also serves the built React bundle. We're switching to Vercel. Vercel is serverless — there is no long-running FastAPI process — so the hosting model has to change. This doc captures the new architecture, the gotchas that come with serverless Python, and the deltas to the main spec.

The assignment requirements (FastAPI backend, cloud Postgres with constraints, React+TS frontend, real auth, public cloud URL, tests + CI) are all still met. The only thing that changes is *where* code runs and *how* it gets deployed.

## 2. Architecture

One Vercel project hosts both halves of the app.

```
                  ┌─────────────────────────────────────┐
                  │  Browser (React + TS + Vite build)  │
                  │  - supabase-js: auth, realtime sub  │
                  │  - fetch: /api/* for everything else│
                  └────────┬──────────────────┬─────────┘
                           │ HTTPS            │ WSS
                           │ /api/*           │ realtime channels
                           ▼                  ▼
              ┌──────────────────────┐  ┌──────────────────┐
              │  Vercel              │  │  Supabase        │
              │  - static SPA (CDN)  │  │  Auth (JWT)      │
              │  - Python function   │  │  Postgres        │
              │    @ /api/* (FastAPI)│◄─┤  Realtime        │
              │  - verifies SB JWT   │  │                  │
              └──────────┬───────────┘  └────────▲─────────┘
                         │                       │
                         └── DATABASE_URL ───────┘
                            (pooler, port 6543)
```

**Key differences vs. Railway model**:

- The React `dist/` is **not** served by FastAPI anymore. Vercel serves it as a static site from its CDN.
- FastAPI runs **per-request** as a Python serverless function. No persistent process, no in-process connection pool, no background tasks.
- Deploy is driven by Vercel's git integration, not by a webhook from CI.

**Why this is fine for synzoia**:

- All endpoints are short (DB query → JSON). Nothing approaches the 10s function timeout (Vercel Hobby tier).
- Realtime fan-out lives in Supabase, not in FastAPI. We never needed to keep websockets open on the API server.
- Connection pooling moves from SQLAlchemy to Supabase's pgbouncer pooler (see §5).
- No cron / background jobs in scope — leaderboards recompute on read, streaks update inline.

**Trade-off accepted**: Python cold starts (~300ms–2s on first hit per function instance). For an app a small group of friends uses daily, this is invisible. If it became a problem we could move the backend to a long-lived host without touching the frontend.

## 3. Repo layout

Additive — CLAUDE.md's documented `backend/` and `frontend/` layout stays intact. Vercel just needs an entrypoint and a config file.

```
api/
  index.py            # 3-line shim that re-exports the FastAPI app
backend/
  app/                # exactly as documented in CLAUDE.md
    main.py
    auth.py
    db.py
    models/
    routes/
    services/
    schemas/
  migrations/         # Alembic, unchanged
  requirements.txt
  tests/
frontend/             # unchanged
vercel.json           # build + routing config
```

`api/index.py` is the smallest possible shim:

```python
from backend.app.main import app  # noqa: F401  -- Vercel discovers `app`
```

Vercel's `@vercel/python` builder finds a top-level `app` object in `api/index.py` and wraps it with an ASGI handler. All FastAPI routing happens inside the imported `app`.

## 4. `vercel.json` (sketch — finalized in implementation)

Two builds and a rewrite:

```json
{
  "version": 2,
  "builds": [
    { "src": "frontend/package.json", "use": "@vercel/static-build",
      "config": { "distDir": "dist" } },
    { "src": "api/index.py", "use": "@vercel/python",
      "config": { "includeFiles": "backend/**" } }
  ],
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/index.py" },
    { "source": "/(.*)",     "destination": "/frontend/dist/$1" }
  ]
}
```

Three things to verify when wiring this up:

1. `includeFiles: "backend/**"` actually pulls the FastAPI source into the function bundle. (Vercel's Python builder is picky about layout — if the simple form doesn't work, fall back to symlinking or moving code into `api/_lib/`.)
2. SPA fallback works: unknown routes serve `frontend/dist/index.html`, not a 404. The catch-all rewrite at the end handles this when combined with Vite's `index.html`.
3. `requirements.txt` location — Vercel looks at the root or alongside the function. We'll either place a copy at the repo root or point to `backend/requirements.txt` via builder config.

These are implementation-time decisions; they don't change the design.

## 5. Database connections — the serverless gotcha

This is the one thing that *will* break if we copy the Railway-era spec verbatim.

- Each function invocation is a fresh process. Holding a SQLAlchemy connection pool inside it does nothing — the pool gets garbage-collected at the end of the request.
- We must connect through **Supabase's pgbouncer pooler** (`<project>.pooler.supabase.com:6543`, transaction mode), not the direct Postgres port (5432). The pooler keeps the real Postgres connections warm; our function just borrows one per request.
- SQLAlchemy engine configuration:

  ```python
  from sqlalchemy.pool import NullPool
  engine = create_engine(DATABASE_URL, poolclass=NullPool, future=True)
  ```

  `NullPool` opens-and-closes on every checkout. With the pooler in front, that's cheap.

- A comment in `backend/app/db.py` explains why — this is the kind of "why is it like this" detail that needs to survive in code, not just in this doc.

## 6. Environment variables

Configured on the Vercel project, scoped to Production + Preview + Development.

**Backend (server-only, never exposed to client)**

| Name | Source | Notes |
|---|---|---|
| `SUPABASE_URL` | Supabase project settings | Used by FastAPI for JWT JWKs lookup |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Bypasses RLS; backend writes |
| `DATABASE_URL` | Supabase pooler URI | **Must be pooler URL, port 6543** |

**Frontend (build-time, `VITE_` prefix → bundled into the React build)**

| Name | Source | Notes |
|---|---|---|
| `VITE_SUPABASE_URL` | Same as `SUPABASE_URL` | Public; safe to ship to browser |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key | Public; RLS is the real gate |

Local `.env` files mirror these for dev. `.env.example` checked into both `backend/` and `frontend/`.

**One Supabase project for prod + previews** in v1. Defensible because the dataset is "5 friends posting sleep" and the cost of seeding a separate staging DB is higher than the cost of an accidental write during a preview demo. Revisit only if previews start to interfere with prod data (they won't, given the auth-gated nature of every endpoint).

## 7. CI/CD

GitHub Actions still runs `.github/workflows/ci.yml` on every push and PR: lint (ruff + eslint) + typecheck (mypy + tsc) + pytest + vitest, against a Postgres service container. Identical to spec §8.

**What changes is deploy**:

- Vercel's git integration is on. Every push to a branch produces a preview URL. Every push to `main` produces the production deploy.
- CI does not deploy. CI gates *merge*: a GitHub branch protection rule on `main` requires the CI status check to pass before a PR can merge. Vercel deploys whatever lands on `main` after that gate.
- `RAILWAY_TOKEN` secret is dropped. No Vercel token is required because git integration handles auth via the GitHub app.

**Migrations**:

- Alembic runs as a step in the `main` CI workflow, against the Supabase DB, before Vercel's deploy completes. Forward-only, no down-migrations applied automatically.
- For PR previews, migrations are *not* auto-applied. If a PR introduces a migration, the author runs it manually against the shared Supabase before merging — captured in the PR description.

This pattern is comfortable for a 3-week build with 3 contributors. If migration coordination becomes painful we add a per-branch ephemeral Supabase later.

## 8. Deltas to the existing spec

Concrete edits to make alongside this doc:

- [`2026-05-16-synzoia-design.md`](./2026-05-16-synzoia-design.md) §2 table: "Public cloud URL" row — replace "Railway" with "Vercel".
- §3 (Architecture): replace the Railway diagram + prose with §2 of this doc, or add a pointer to this doc.
- §8 (Testing + CI): update the deploy paragraph and secrets list.
- `CLAUDE.md` "Stack" line: replace "Railway hosting" with "Vercel hosting".
- `CLAUDE.md` "Push back if Claude tries to…" — consider adding: "Suggesting FastAPI hold a connection pool. We're on serverless; use NullPool + Supabase pooler."

These edits land together with the first commit that wires up `vercel.json` and `api/index.py`.

## 9. What is explicitly NOT changing

- Database schema (§4 of main spec): unchanged.
- API endpoints (§5 of main spec): unchanged. Same paths, same auth model, same JSON shapes.
- Nontrivial logic (§6 of main spec): unchanged. Leaderboard and streaks code is the same regardless of where it runs.
- Frontend architecture (§7 of main spec): unchanged. Same routes, same React Query patterns, same Supabase Realtime subscriptions.
- Team ownership (§9 of main spec): unchanged.

## 10. Open questions

1. **`requirements.txt` location** — root vs. `backend/`. Resolve at implementation time once we test which form Vercel's Python builder accepts cleanly. Doesn't affect design.
2. **Staging Supabase** — sticking with one project for v1. Revisit only if preview deploys interfere with prod data.
3. **Custom domain** — assignment requires a public URL; the default `*.vercel.app` URL satisfies that. A custom domain is a nice-to-have, not in scope here.
