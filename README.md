# synzoia

> A small private group for tracking how you sleep alongside friends. You and 2-5 people create a "crew," post last night's sleep, see each other's posts in a real-time feed, react, chat, and watch a rolling weekly leaderboard. The point is friends knowing how each other are recovering, not anonymous health data in a void.

- **Live URL**: _TBD — fill in once deployed_
- **GitHub**: _TBD — fill in once pushed_
- **Tier targeted**: Gold (real-time + group chat + reactions on top of bronze + silver invariants)

## Team

- **Micah Briggs** (rbriggs@student.uaustin.org) — crews, auth, leaderboard, repo conventions, CI
- **Teammate A** — sleep posts, HealthKit ingestion, streaks, feed, profile pages
- **Teammate B** — group chat, reactions, realtime infra, visual design pass

## Nontrivial logic

Two pieces (gold-tier mentions both, plus the gold pick-one):

1. **Rolling group leaderboard** — `backend/app/services/leaderboard.py::compute_leaderboard()`
   Aggregates sleep posts per group member over a configurable window (7d / 30d / all-time) in the caller's timezone. Composite score from coverage (% nights posted), mean duration (8h baseline, oversleep penalty), and consistency (stddev of bedtime). Members below a min-coverage threshold are listed as "showing up next week" without a score. Tiebreakers: coverage → mean duration → join date.

2. **Timezone-aware streaks** — `backend/app/services/streaks.py::recompute_streak()`
   Materialized streak counter updated transactionally on every sleep post insert. Streak counts consecutive `night_of` dates in the user's IANA timezone. Today is a grace day — streak alive until the most recent missing date is yesterday or earlier. DST handled via `zoneinfo`.

**Gold pick-one — real-time updates**: Feed posts, reactions, and chat messages broadcast via Supabase Realtime (WAL → channels). Frontend subscribes per group; updates appear in <1s without a manual refresh. See `frontend/src/hooks/useGroupRealtime.ts`.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite + Tailwind | Class default; deliverable spec |
| Backend | FastAPI (Python) | Class default; deliverable spec |
| Database | Supabase Postgres | Class default; powers Auth + Realtime in one provider |
| Auth | Supabase Auth | Don't roll your own; JWT verified server-side |
| Realtime | Supabase Realtime | Frontend subscribes directly via supabase-js |
| Hosting | Railway (one service, FastAPI serves built React + /api/*) | One URL, no CORS, deploy-on-push |
| CI | GitHub Actions | Gates merge to main on green tests |

## Design decisions

_Fill in 3-4 specific decisions with reasoning before submission. Examples drafted in [docs/superpowers/specs/2026-05-16-synzoia-design.md](docs/superpowers/specs/2026-05-16-synzoia-design.md) §4 (schema decisions) and §6 (logic decisions)._

## Where Claude helped / where we pushed back

_Fill in honest one-paragraph reflection before submission. Read across the cohort by the professor — not graded._

## Run locally

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env  # fill in VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE
npm run dev
```

## Run tests

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm test
```

## Design doc

Full spec lives at [docs/superpowers/specs/2026-05-16-synzoia-design.md](docs/superpowers/specs/2026-05-16-synzoia-design.md). HealthKit bridge research for the sleep-ingestion path lives at [docs/healthkit-research.md](docs/healthkit-research.md).
