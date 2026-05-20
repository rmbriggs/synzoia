# Vercel Hosting Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get synzoia deployable to Vercel end-to-end — Vite/React frontend served as a static SPA, a minimal FastAPI backend running as a Python serverless function at `/api/*`, verified locally with `vercel dev` and on a Vercel preview URL with a real Supabase DB connection.

**Architecture:** Single Vercel project. Repo root holds `vercel.json` plus an `api/index.py` shim that re-exports a FastAPI `app` defined in `backend/app/main.py`. Vercel's `@vercel/python` builder bundles the `backend/` directory into the function and serves it on demand. Frontend stays in `frontend/`, built by `@vercel/static-build` to `frontend/dist`. SQLAlchemy uses `NullPool` and connects through Supabase's pgbouncer pooler (port 6543), because the function is stateless and pooling lives in Supabase.

**Tech Stack:** FastAPI, SQLAlchemy (with `NullPool`), `psycopg[binary]` v3, pytest + httpx for tests, Vercel `@vercel/python` + `@vercel/static-build`, Supabase (Postgres + Auth + Realtime). Vite + React 19 frontend already exists.

**Out of scope for this plan:** the full set of API endpoints (`/api/me`, `/api/groups/*`, etc.), GitHub Actions CI, Alembic migrations, real DB tables. Those are separate plans. This one stops once the deploy pipeline is proven working with a `/api/health` endpoint.

---

## File structure

| Path | Action | Responsibility |
|---|---|---|
| `vercel.json` | create | Two builds (frontend static, python function) + rewrites (`/api/*` → function, fallthrough → SPA) |
| `requirements.txt` (repo root) | create | `-r backend/requirements.txt` — points Vercel's Python builder at the backend deps |
| `api/index.py` | create | 3-line shim: `from backend.app.main import app` |
| `backend/requirements.txt` | create | Runtime deps: `fastapi`, `sqlalchemy`, `psycopg[binary]`, `python-dotenv` |
| `backend/requirements-dev.txt` | create | `-r requirements.txt` + `pytest`, `httpx` |
| `backend/pyproject.toml` | create | Minimal pytest config (testpaths, pythonpath) |
| `backend/.env.example` | create | Server-only env var names + comments |
| `backend/app/__init__.py` | create | Empty package marker |
| `backend/app/main.py` | create | FastAPI app + `GET /api/health` |
| `backend/app/db.py` | create | `get_engine()` returning a `NullPool` engine, lazily |
| `backend/tests/__init__.py` | create | Empty package marker |
| `backend/tests/conftest.py` | create | Sets `DATABASE_URL` env var for tests |
| `backend/tests/test_health.py` | create | TestClient hits `/api/health` |
| `backend/tests/test_db.py` | create | Asserts engine uses `NullPool` |
| `frontend/.env.example` | create | `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` |
| `.gitignore` | modify | Add `.env`, `.vercel/`, `__pycache__/`, `.pytest_cache/`, `*.pyc` if missing |
| `CLAUDE.md` | modify | Replace "Railway" stack/notes with Vercel |
| `docs/superpowers/specs/2026-05-16-synzoia-design.md` | modify | §2 table row, §3 architecture, §8 deploy paragraph + secrets |

---

## Task 1: Backend Python skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.6
sqlalchemy==2.0.36
psycopg[binary]==3.2.13
python-dotenv==1.0.1
```

- [ ] **Step 2: Create `backend/requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.4
httpx==0.28.1
```

- [ ] **Step 3: Create `backend/pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = [".."]
```

The `pythonpath = [".."]` lets tests do `from backend.app.main import app` while running with `pytest` from the `backend/` directory.

- [ ] **Step 4: Create `backend/app/__init__.py`** (empty file)

- [ ] **Step 5: Create `backend/tests/__init__.py`** (empty file)

- [ ] **Step 6: Create `backend/tests/conftest.py`**

```python
import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:6543/test",
)
```

This gives `backend/app/db.py` a value to read at import time during tests. Tests don't actually connect — they just verify configuration.

- [ ] **Step 7: Update `.gitignore` if needed**

Run `cat .gitignore` and confirm it contains these entries (add any missing):

```
.env
.env.*.local
.vercel/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 8: Create a Python virtualenv and install dev deps**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Expected: clean install, no errors. (If `psycopg[binary]` fails to install on your machine, switch to `psycopg-binary` or install Postgres dev headers — note this in the PR.)

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt backend/requirements-dev.txt backend/pyproject.toml \
        backend/app/__init__.py backend/tests/__init__.py backend/tests/conftest.py \
        .gitignore
git commit -m "feat(backend): scaffold Python project with pytest + FastAPI deps"
```

---

## Task 2: `/api/health` endpoint (TDD)

**Files:**
- Test: `backend/tests/test_health.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
```

- [ ] **Step 2: Run test to verify it fails**

From `backend/` with the venv active:

```bash
pytest tests/test_health.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.main'` (or similar — `main.py` doesn't exist yet).

- [ ] **Step 3: Write the minimal implementation**

`backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="synzoia")


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_health.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_health.py
git commit -m "feat(backend): add /api/health endpoint"
```

---

## Task 3: `db.py` with `NullPool` (TDD)

**Files:**
- Test: `backend/tests/test_db.py`
- Create: `backend/app/db.py`

The point of this file is to lock in the rule that the engine uses `NullPool`. That's the serverless-correctness invariant, and a test makes future drift visible.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_db.py`:

```python
from sqlalchemy.pool import NullPool

from backend.app import db


def test_engine_uses_null_pool():
    """Serverless functions must not pool DB connections themselves;
    that job belongs to Supabase's pgbouncer pooler."""
    db.get_engine.cache_clear()
    engine = db.get_engine()
    assert isinstance(engine.pool, NullPool)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_db.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.db'`.

- [ ] **Step 3: Write the minimal implementation**

`backend/app/db.py`:

```python
"""Database engine factory.

Serverless functions cannot maintain their own connection pool — each
invocation is a fresh process. Pooling lives in Supabase's pgbouncer
(connect via the *pooler* URL on port 6543, transaction mode). The
SQLAlchemy engine here uses NullPool so it opens-and-closes per checkout.
"""

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = os.environ["DATABASE_URL"]
    return create_engine(url, poolclass=NullPool, future=True)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_db.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: 2 passed (health + db).

- [ ] **Step 6: Commit**

```bash
git add backend/app/db.py backend/tests/test_db.py
git commit -m "feat(backend): add NullPool engine factory in db.py"
```

---

## Task 4: `api/index.py` shim

**Files:**
- Create: `api/index.py`

- [ ] **Step 1: Create `api/index.py`**

```python
"""Vercel entrypoint. The real FastAPI app lives in backend/app/main.py;
this shim only exists so Vercel's @vercel/python builder finds an ASGI
`app` object at the conventional location."""

from backend.app.main import app  # noqa: F401
```

- [ ] **Step 2: Verify the import works**

From the repo root, with the backend venv active:

```bash
PYTHONPATH=. python -c "from api.index import app; print(type(app).__name__)"
```

Expected output: `FastAPI`

- [ ] **Step 3: Commit**

```bash
git add api/index.py
git commit -m "feat: add Vercel python entrypoint shim at api/index.py"
```

---

## Task 5: Root `requirements.txt` and `vercel.json`

**Files:**
- Create: `requirements.txt` (repo root)
- Create: `vercel.json`

- [ ] **Step 1: Create the root `requirements.txt`**

```
-r backend/requirements.txt
```

This is the file Vercel's Python builder will discover at the repo root. The `-r` directive defers to the backend's deps file, so `backend/requirements.txt` stays the source of truth (consistent with CLAUDE.md).

- [ ] **Step 2: Create `vercel.json`**

```json
{
  "version": 2,
  "builds": [
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": { "distDir": "dist" }
    },
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": { "includeFiles": "backend/**" }
    }
  ],
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/index.py" },
    { "source": "/(.*)",     "destination": "/frontend/dist/$1" }
  ]
}
```

Notes for the implementer:
- The two `rewrites` are evaluated top-to-bottom. `/api/*` matches first and routes to the Python function; everything else falls through to the static SPA.
- `includeFiles: "backend/**"` pulls the FastAPI source into the function bundle. Without it, the import in `api/index.py` would fail at runtime.
- If Vercel's static-build can't find a `build` script in `frontend/package.json`, double-check it exists (it does in the current repo: `"build": "tsc -b && vite build"`).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt vercel.json
git commit -m "feat: add vercel.json + root requirements.txt for monorepo deploy"
```

---

## Task 6: `.env.example` files

**Files:**
- Create: `backend/.env.example`
- Create: `frontend/.env.example`

- [ ] **Step 1: Create `backend/.env.example`**

```
# Supabase project URL — used by FastAPI to fetch JWT JWKs
SUPABASE_URL=https://<project-ref>.supabase.co

# Supabase service-role key — bypasses RLS; backend writes
SUPABASE_SERVICE_KEY=

# Supabase POOLER URL (port 6543, transaction mode).
# Must NOT be the direct port 5432 URL — serverless functions need
# the pgbouncer pooler so connections are kept warm on Supabase's side.
# Format: postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
DATABASE_URL=
```

- [ ] **Step 2: Create `frontend/.env.example`**

```
# Public Supabase URL — same value as backend SUPABASE_URL
VITE_SUPABASE_URL=https://<project-ref>.supabase.co

# Public anon key — safe to ship to the browser; RLS is the real gate
VITE_SUPABASE_ANON_KEY=
```

- [ ] **Step 3: Commit**

```bash
git add backend/.env.example frontend/.env.example
git commit -m "docs: document required env vars for backend and frontend"
```

---

## Task 7: Local verification with `vercel dev`

**Files:** none modified — this is verification only.

- [ ] **Step 1: Install the Vercel CLI if needed**

```bash
vercel --version
```

Expected: a version number. If not installed: `npm install -g vercel`.

- [ ] **Step 2: Populate a local `.env` for the backend**

Copy `backend/.env.example` to `backend/.env` and fill in the three values from the Supabase project dashboard. **Make sure `DATABASE_URL` is the pooler URL with port 6543**, not the direct connection.

- [ ] **Step 3: Populate a local `.env` for the frontend**

Copy `frontend/.env.example` to `frontend/.env` and fill in the two `VITE_` values.

- [ ] **Step 4: Link the project to Vercel (creates `.vercel/` locally)**

From the repo root:

```bash
vercel link
```

Walk through the prompts: scope = your personal scope, project = new (`synzoia`).

- [ ] **Step 5: Run `vercel dev`**

```bash
vercel dev
```

Expected: a local URL (typically `http://localhost:3000`) that proxies both the static frontend and the Python function.

- [ ] **Step 6: Smoke test the function**

In another terminal:

```bash
curl -sS http://localhost:3000/api/health
```

Expected output: `{"ok":true}`

- [ ] **Step 7: Smoke test the frontend**

Open `http://localhost:3000/` in a browser. Expected: the existing synzoia frontend renders normally. Refreshing a deep route (e.g. `http://localhost:3000/dashboard`) should also serve `index.html`, not 404.

- [ ] **Step 8: Stop `vercel dev`**

Ctrl-C in the terminal running it. No commit — nothing changed in the repo.

---

## Task 8: Configure env vars in Vercel and deploy a preview

**Files:** none modified — this is a deploy step.

- [ ] **Step 1: Add backend env vars to the Vercel project**

In the Vercel dashboard for the `synzoia` project → Settings → Environment Variables, add each of these for **Production**, **Preview**, and **Development**:

- `SUPABASE_URL` → same value as the local `.env`
- `SUPABASE_SERVICE_KEY` → same value as the local `.env`
- `DATABASE_URL` → the pooler URL (port 6543)

CLI alternative for each variable:

```bash
vercel env add SUPABASE_URL
# (paste value when prompted; select Production, Preview, Development with space)
```

- [ ] **Step 2: Add frontend env vars to the Vercel project**

Same dashboard, same three environments:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

- [ ] **Step 3: Trigger a preview deploy**

```bash
vercel
```

Expected: the CLI prints a preview URL like `https://synzoia-<hash>-<scope>.vercel.app`. Build logs should show both the frontend build and the Python function build succeeding.

- [ ] **Step 4: Smoke test the preview deploy**

```bash
curl -sS https://<your-preview-url>/api/health
```

Expected: `{"ok":true}`.

Open the preview URL in a browser. Expected: the existing frontend loads against the real Supabase project (sign-in works if Supabase auth is already configured for the existing local dev).

- [ ] **Step 5: If `/api/health` returns 500 or 404, debug:**

- 404: check the `rewrites` order in `vercel.json` — `/api/(.*)` must come *before* the catch-all `/(.*)`.
- 500: open the function logs in the Vercel dashboard. Most likely: missing import (`backend/` not in `includeFiles`) or missing env var.
- If frontend 404s on deep routes: the SPA fallback rewrite isn't matching — verify the catch-all `destination` points at `/frontend/dist/$1`.

No commit yet — fix `vercel.json` if needed, commit the fix, then re-deploy.

---

## Task 9: Update CLAUDE.md and the main spec

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-05-16-synzoia-design.md`

- [ ] **Step 1: Update `CLAUDE.md` — stack line**

Open `CLAUDE.md`. Find the line under "Project at a glance":

```
**Stack**: FastAPI (Python) + React/TS + Vite + Tailwind + Supabase Postgres/Auth/Realtime + Railway hosting.
```

Replace `Railway hosting` with `Vercel hosting (FastAPI as Python serverless functions)`.

- [ ] **Step 2: Update `CLAUDE.md` — add a serverless-pooling pushback bullet**

Under the "Push back if Claude tries to..." section, add this bullet at the end of the list:

```
- Configuring SQLAlchemy with a real connection pool. We deploy on Vercel serverless — use `NullPool` and connect via Supabase's pgbouncer pooler (port 6543).
```

- [ ] **Step 3: Update main spec `§2` table row**

Open `docs/superpowers/specs/2026-05-16-synzoia-design.md`. In the table in §2, find:

```
| Public cloud URL | Railway (FastAPI serves built React + /api/*) |
```

Replace with:

```
| Public cloud URL | Vercel (static SPA + FastAPI as Python serverless function at /api/*) |
```

- [ ] **Step 4: Update main spec `§3` (Architecture) — replace the section body**

Replace everything from the first sentence of §3 ("One Railway service hosting FastAPI...") through the end of the architecture diagram with a short paragraph pointing at the new doc:

```markdown
## 3. Architecture

Single Vercel project hosts both halves. The Vite/React build is served as a static SPA from Vercel's CDN; FastAPI runs as a Python serverless function mounted at `/api/*`. Supabase provides auth, Postgres, and realtime. Detailed architecture (with diagram), the serverless DB-connection rule, and the deploy model are in [`2026-05-20-vercel-hosting-design.md`](./2026-05-20-vercel-hosting-design.md).
```

Leave the rest of §3 ("**Key flows**:" onward) intact — those flows describe the request lifecycle, which doesn't change.

- [ ] **Step 5: Update main spec `§8` — deploy paragraph and secrets list**

In §8 ("Testing + CI"), find this block in "### CI — `.github/workflows/ci.yml`":

```
2. On push to `main`: same + deploy step (Railway auto-deploy on green via webhook)
3. Required check: tests must pass before merge to `main`
4. Secrets: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `DATABASE_URL`, `RAILWAY_TOKEN`
```

Replace with:

```
2. On push to `main`: same checks. Deploy is handled separately by Vercel's git integration (auto-deploys every push: branches → preview URLs, `main` → production). CI does not deploy; it only gates merges.
3. Required check: tests must pass before merge to `main` (enforced via GitHub branch protection).
4. Secrets used in CI: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `DATABASE_URL`. No `VERCEL_TOKEN` is required because the Vercel GitHub App handles deploy auth.
```

- [ ] **Step 6: Commit doc updates**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-05-16-synzoia-design.md
git commit -m "docs: align CLAUDE.md and main spec with Vercel hosting"
```

---

## Task 10: Final verification + push

- [ ] **Step 1: Run the full backend test suite one more time**

From `backend/` with the venv active:

```bash
pytest -v
```

Expected: 2 passed.

- [ ] **Step 2: Run the frontend tests**

From `frontend/`:

```bash
npm run test
```

Expected: existing tests pass (no regressions from this plan — we didn't touch frontend code).

- [ ] **Step 3: Run `vercel dev` one more time and re-verify**

```bash
vercel dev
curl -sS http://localhost:3000/api/health
```

Expected: `{"ok":true}`.

- [ ] **Step 4: Push to `main`**

```bash
git push origin main
```

Vercel will pick up the push and run a production deploy. Watch the build in the Vercel dashboard.

- [ ] **Step 5: Verify the production deploy**

```bash
curl -sS https://<production-url>/api/health
```

Expected: `{"ok":true}`.

Open the production URL in a browser. Expected: synzoia frontend loads, signs in, and renders normally.

---

## Done state

- `https://<vercel-url>/` serves the synzoia frontend.
- `https://<vercel-url>/api/health` returns `{"ok": true}` from FastAPI.
- `backend/` contains a working FastAPI app with two passing tests.
- `CLAUDE.md` and the main spec describe the Vercel hosting model.
- The team can ship features by adding routes under `backend/app/routes/` and adding tests, without touching deploy infra.
