# synzoia — Design Spec

**Date**: 2026-05-16
**Class**: Software Engineering — UATX — Spring 2026
**Project**: Final project
**Team**: 3 people (Micah + 2 teammates)
**Tier target**: Gold
**Due**: Day of lecture 10.2 (3-week build window)

---

## 1. Pitch

A small private group for tracking how you sleep alongside friends. You and 2-5 people create a "crew," post last night's sleep, see each other's posts in a real-time feed, react, chat, and watch a rolling weekly leaderboard. The point is friends knowing how each other are recovering, not anonymous health data in a void.

## 2. Why this satisfies the assignment

Mapping to the invariants in the project PDF:

| Invariant | How synzoia hits it |
|---|---|
| FastAPI backend, 6-7 endpoints | 11 endpoints in §5 |
| Nontrivial logic | Two pieces: rolling leaderboard + timezone-aware streaks (§6) |
| Cloud-hosted Postgres with real FKs + constraints | Supabase Postgres, 8 tables with FKs + CHECK constraints (§4) |
| React + TypeScript frontend | Vite + React + TS, single-page app (§7) |
| Real user identity | Supabase Auth, JWT-verified on every API call |
| Multi-user value | A crew is meaningless solo — you need other people in it for the feed, leaderboard, and chat to mean anything |
| Test suite + CI | ~10 pytest + 2 Vitest, GitHub Actions gating deploy (§8) |
| Public cloud URL | Vercel (static SPA + FastAPI as Python serverless function at /api/*) |
| Public GitHub repo | TBD repo name, set up after spec lock |
| README | Drafted at end of build, covers all 9 required sections |

**Gold-tier specifics**:
- Mobile-friendly UI (single-column < 640px, bottom tab bar on phone)
- Pick-one: **real-time** updates via Supabase Realtime (feed, chat, reactions)
- Custom feature 1: **group chat** threaded inside each crew
- Custom feature 2: **kudos/reactions** on sleep posts with optimistic UI

## 3. Architecture

Single Vercel project hosts both halves. The Vite/React build is served as a static SPA from Vercel's CDN; FastAPI runs as a Python serverless function mounted at `/api/*`. Supabase provides auth, Postgres, and realtime. Detailed architecture (with diagram), the serverless DB-connection rule, and the deploy model are in [`2026-05-20-vercel-hosting-design.md`](./2026-05-20-vercel-hosting-design.md).

**Key flows**:

1. **Sign in**: React → `supabase.auth.signInWithPassword()` → JWT stored client-side → every fetch to `/api/*` sends `Authorization: Bearer <jwt>` → FastAPI verifies JWT against Supabase JWKs and resolves `user_id`.
2. **Post sleep**: React POSTs `/api/sleep` → FastAPI inserts → row appears in `sleep_posts` → Supabase Realtime broadcasts the insert → every group member's open feed receives the new post in their subscription callback.
3. **Chat message**: POST `/api/groups/{id}/messages` → row inserted → realtime broadcasts → other members see it appear.
4. **Leaderboard**: GET `/api/groups/{id}/leaderboard?window=7d` → FastAPI runs aggregation → returns ranked list. Recomputed on each fetch; cheap at this scale.

**Why the split**: FastAPI owns writes + business logic + nontrivial queries. Supabase owns auth (don't roll your own) and realtime fan-out (don't run websocket plumbing yourself). The two systems share one database — FastAPI writes a row, Supabase Realtime sees the WAL change, broadcasts it.

**RLS gotcha**: Supabase Realtime needs Row-Level Security policies on broadcast tables. Policy: "user can subscribe to rows in groups they are a member of." FastAPI uses the service role key, bypassing RLS for its writes.

## 4. Database schema

8 tables, all in `public` schema. Migrations live in `backend/migrations/` (Alembic).

```sql
-- profiles : 1:1 with auth.users
create table profiles (
  id              uuid primary key references auth.users(id) on delete cascade,
  username        text not null unique check (char_length(username) between 3 and 30),
  display_name    text not null check (char_length(display_name) <= 60),
  timezone        text not null default 'America/Chicago',
                  -- IANA tz; critical for streak + leaderboard windowing
  avatar_url      text,
  created_at      timestamptz not null default now()
);

-- groups : a "crew"
create table groups (
  id              uuid primary key default gen_random_uuid(),
  name            text not null check (char_length(name) between 1 and 60),
  invite_code     text not null unique check (char_length(invite_code) = 8),
  created_by      uuid not null references profiles(id) on delete restrict,
  created_at      timestamptz not null default now()
);

-- memberships : M:N users to groups
create table memberships (
  group_id        uuid not null references groups(id) on delete cascade,
  user_id         uuid not null references profiles(id) on delete cascade,
  role            text not null default 'member' check (role in ('owner','member')),
  joined_at       timestamptz not null default now(),
  primary key (group_id, user_id)
);
create index on memberships (user_id);

-- sleep_posts : one night's sleep, shared to ONE group
create table sleep_posts (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references profiles(id) on delete cascade,
  group_id        uuid not null references groups(id) on delete cascade,
  night_of        date not null,
                  -- The date the sleep counts against, in user's tz.
                  -- 11pm-7am sleep counts for 11pm's date.
                  -- 2am-10am sleep counts for the previous day's date.
  bedtime         timestamptz not null,
  wake_time       timestamptz not null check (wake_time > bedtime),
  duration_min    integer not null check (duration_min between 1 and 1440),
  quality_score   integer check (quality_score between 1 and 100),
  source          text not null check (source in
                  ('manual','shortcut','healthkit_xml','terra','other')),
  note            text check (char_length(note) <= 280),
  created_at      timestamptz not null default now(),
  unique (user_id, group_id, night_of)
);
create index on sleep_posts (group_id, night_of desc);
create index on sleep_posts (user_id, night_of desc);

-- sleep_stages : optional per-stage breakdown (HealthKit gives this)
create table sleep_stages (
  id              bigserial primary key,
  sleep_post_id   uuid not null references sleep_posts(id) on delete cascade,
  stage           text not null check (stage in ('awake','rem','core','deep')),
  duration_min    integer not null check (duration_min > 0)
);
create index on sleep_stages (sleep_post_id);

-- reactions : kudos / emoji on sleep posts
create table reactions (
  sleep_post_id   uuid not null references sleep_posts(id) on delete cascade,
  user_id         uuid not null references profiles(id) on delete cascade,
  emoji           text not null check (emoji in ('💪','😴','🔥','🫡','🥱')),
  created_at      timestamptz not null default now(),
  primary key (sleep_post_id, user_id, emoji)
);
create index on reactions (sleep_post_id);

-- messages : group chat
create table messages (
  id              bigserial primary key,
  group_id        uuid not null references groups(id) on delete cascade,
  user_id         uuid not null references profiles(id) on delete cascade,
  body            text not null check (char_length(body) between 1 and 1000),
  created_at      timestamptz not null default now()
);
create index on messages (group_id, created_at desc);

-- streaks : materialized streak counts per user
create table streaks (
  user_id         uuid primary key references profiles(id) on delete cascade,
  current_streak  integer not null default 0,
  longest_streak  integer not null default 0,
  last_night_of   date,
  updated_at      timestamptz not null default now()
);
```

**Schema design decisions** (these flow into README §6):

1. **`night_of` is a `date` in the poster's timezone, stored explicitly.** Bucketing happens once at insert; leaderboard + streak queries use a simple `WHERE night_of BETWEEN ...`. Avoids re-deriving from `bedtime` on every query.
2. **`profiles` is separate from `auth.users`.** Supabase Auth owns identity; we own profile fields. Linked 1:1 by id. Survives auth provider changes.
3. **A sleep post belongs to one group.** Cross-posting requires two rows. Simplifies feed query, RLS, and "who can see this post."
4. **`reactions` uses a fixed emoji set.** Free-form emoji is a moderation rabbit hole. Five emojis cover encouragement / sympathy / hype / respect / relatability.
5. **`streaks` is materialized, not computed on read.** Streak query with gap detection is expensive; we hit it on profile + leaderboard. Updated transactionally on sleep_post insert.
6. **Indexes are deliberate, not exhaustive.** Three indexes for the three hot queries; add more only when measured.

**Not in v1**: friendships table (groups are the only social unit), competitions table (rolling leaderboards are computed from `sleep_posts`, no state), notifications table (realtime delivers updates while user is on-page), comments table (reactions cover the engagement need).

**RLS policies** (Supabase requirement for realtime):
- `sleep_posts`, `reactions`, `messages`: SELECT allowed if `auth.uid()` is in `memberships` for that `group_id`.
- `sleep_stages`: SELECT allowed if the parent `sleep_post` is visible.
- `profiles`: SELECT allowed for any authed user (display names are public-ish).
- `streaks`: SELECT allowed for any authed user who shares a group with the streak owner.
- FastAPI uses service role key, bypasses RLS for writes.

## 5. API endpoints

All under `/api/`. All auth-gated (Bearer JWT) except where noted.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/me` | Whoami: profile + my groups. Called on app load. |
| `POST` | `/api/groups` | Create a crew. Returns row + generated 8-char invite code. |
| `POST` | `/api/groups/join` | Body: `{invite_code}`. Adds caller to memberships. 404 on bad code. |
| `GET` | `/api/groups/{id}/feed` | Sleep posts for the group, newest first. Includes display name, reaction counts, my-reactions. Paginated by `before` cursor. |
| `POST` | `/api/sleep` | Post a night's sleep. Computes `night_of`. Upserts on `(user_id, group_id, night_of)`. Updates `streaks` in same transaction. |
| `POST` | `/api/sleep/{id}/react` | Body: `{emoji}`. Toggles the reaction. |
| `GET` | `/api/groups/{id}/leaderboard` | Query: `window=7d|30d|all`. **Nontrivial query.** Returns ranked members with stats. |
| `GET` | `/api/users/{id}` | Public-ish profile: display_name, streaks, recent posts (filtered to shared groups). |
| `POST` | `/api/groups/{id}/messages` | Send chat message. Realtime broadcast handles fan-out. |
| `GET` | `/api/groups/{id}/messages` | Chat history, paginated by `before` cursor. |
| `POST` | `/api/healthkit/import` | Sleep-source bridge endpoint. Body shape TBD by teammate's bridge choice (see §10 + `docs/healthkit-research.md`). |

**Cross-cutting concerns**:
- `user_id` resolved from JWT, not request body.
- Group-scoped endpoints check membership; return 403 if not a member.
- Standard codes: 401 unauthed, 403 forbidden, 404 nonexistent, 409 unique-key conflict, 422 validation.
- All endpoints return JSON. Errors return `{error: {code, message}}`.

## 6. Nontrivial logic pieces

### Piece 1 (bronze) — Rolling group leaderboard
**File**: `backend/app/services/leaderboard.py::compute_leaderboard(group_id, window, caller_id)`

**One-line summary**: rank members of this group by how well they slept this week.

**Design decisions buried in that one line**:

1. **Window in caller's timezone**: the leaderboard is rendered for a specific viewer; window is `[today - 6 days, today]` in caller-tz dates, applied against `night_of`. Two viewers in different tz can see slightly different leaderboards on boundary days — accepted.
2. **Composite score**:
   ```
   coverage         = nights_posted_in_window / window_length
   mean_duration_pts = clip(mean_minutes / 480, 0, 1.2)   # 8h = 1.0, oversleep caps at 1.2
   consistency_pts  = 1 - clip(stddev_bedtime_min / 120, 0, 1)  # within 2h of own avg = 1.0
   score = round(100 * (0.5*mean_duration_pts + 0.3*coverage + 0.2*consistency_pts), 1)
   ```
   Weights + constants are inlined with comments. Not user-tunable in v1.
3. **Min-coverage threshold**: members with `coverage < 0.3` get no score, listed at bottom under "showing up next week." Prevents single-post gaming.
4. **Tiebreakers** (in ORDER BY): equal score → higher `coverage` → higher `mean_duration_pts` → earlier `joined_at`.
5. **Inactive members**: zero posts in window → returned with `null` score, `inactive: true` flag. Frontend renders faded.

**Query shape**: CTE filters posts to window → aggregate per user → join to memberships → apply scoring + ordering. Real cross-table aggregation.

### Piece 2 (silver) — Timezone-aware streaks
**File**: `backend/app/services/streaks.py::recompute_streak(user_id, new_post_night_of)`

**One-line summary**: streak = consecutive days the user posted sleep.

**Design decisions**:

1. **Streak in user's timezone** (from `profiles.timezone`). `night_of` already bucketed at insert time, so streak walk is `WHERE night_of <= today AND user_id = ? ORDER BY night_of DESC` and count consecutive dates.
2. **Today is a grace day**: at 11:30pm Sunday in user tz, no Sunday post yet but Saturday is posted → streak alive. Broken only if the most recent missing date is `<= yesterday`.
3. **Timezone change**: old `night_of` values bucketed in old tz; recompute in new tz can mis-bucket seam day. Accepted, documented. Rebucket-on-tz-change is out of scope.
4. **Update on insert, not on read**: `/api/sleep` writes the post and calls `recompute_streak` in the same transaction:
   - `new_post_night_of == last_night_of + 1` → increment
   - `== last_night_of` → no-op (repost)
   - `> last_night_of + 1` → reset to 1
   - Update `longest_streak` if `current_streak` exceeds it
5. **DST**: date arithmetic uses `zoneinfo`-aware Python `date`, not naive `timedelta(days=1)`. Spring-forward/fall-back don't break the count.

**Why not CRUD**: timezone handling + grace-day rule + gap detection on insert + consistency invariant between `sleep_posts` and `streaks` are real design decisions.

## 7. Frontend

React Router with bookmarkable URLs. Vite + React + TypeScript + Tailwind.

| Route | Purpose |
|---|---|
| `/` | Logged out → marketing/sign-in. Logged in → redirect to `/crews`. |
| `/auth` | Sign in / sign up. `supabase-js` form. |
| `/crews` | List my crews + create + join-by-code. |
| `/crews/:id` | Tabs: **Feed** (default) · **Leaderboard** · **Chat**. Tab in URL: `?tab=chat`. |
| `/crews/:id/post` | Post tonight's sleep (modal-ish). |
| `/users/:id` | Public profile: name, streaks, recent posts in shared crews. |
| `/settings` | Timezone, display name, sign out. |

**State**:
- React Query for server data (cache, refetch, optimistic mutations)
- `useAuthSession` hook wrapping `supabase.auth`
- Single `supabase` client instance

**Optimistic updates** (silver):
- Posting sleep: appears in feed immediately; rolls back on 4xx
- Reacting: toggles instantly
- Sending chat: appears immediately marked "sending"; confirmed on echo from realtime

**Realtime subscriptions** (gold pick-one):
- Feed tab: subscribe to `sleep_posts` + `reactions` filtered by `group_id`
- Chat tab: subscribe to `messages` filtered by `group_id`
- Unsubscribe on unmount

**Loading + error states** on every fetch (skeletons + retry buttons).

**Mobile-friendly** (gold): single-column below 640px, bottom tab bar on phone widths, post-sleep form full-screen on phone.

## 8. Testing + CI

### Backend (~10 pytest)
`backend/tests/`:
- `test_auth.py` — no JWT → 401; bad JWT → 401
- `test_groups.py` — create, join with valid + bad code, can't see groups you're not in
- `test_sleep_post.py` — happy path, duplicate `(user, group, night)` upserts, night_of bucketing for late-night post, validation rejects wake < bed
- `test_leaderboard.py` — happy path, member with 1 post lands inactive, tiebreaker correctness, empty group → empty list
- `test_streaks.py` — increment on next-day post, reset on gap, no-op on repost, DST boundary
- `test_reactions.py` — toggle behavior, members-only enforcement

### Frontend (~2 Vitest)
`frontend/src/__tests__/`:
- Leaderboard component renders ranks correctly with mocked data
- `useAuthSession` returns logged-out state when no session

### CI — `.github/workflows/ci.yml`
1. On push to any branch + on PR: lint (ruff + eslint) + typecheck (mypy + tsc) + pytest + vitest
2. On push to `main`: same checks. Deploy is handled separately by Vercel's git integration (auto-deploys every push: branches → preview URLs, `main` → production). CI does not deploy; it only gates merges.
3. Required check: tests must pass before merge to `main` (enforced via GitHub branch protection).
4. Secrets used in CI: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`. No `VERCEL_TOKEN` is required because the Vercel GitHub App handles deploy auth.

### Test DB strategy
GitHub Actions `postgres` service container. Run migrations from scratch. Each test wrapped in a transaction rolled back at teardown. Fast, isolated.

## 9. Team ownership — divide along seams

Per PDF: "you do backend, I do frontend" falls apart. Each teammate owns DB → API → UI for their slice.

### Micah — Crews + Auth + Leaderboard
- Tables: `profiles`, `groups`, `memberships` (+ RLS policies)
- API: `/api/me`, `/api/groups*`, `/api/groups/:id/leaderboard`
- UI: `/auth`, `/crews`, `/crews/:id` shell + leaderboard tab
- **Bronze nontrivial piece**: leaderboard
- Owns `CLAUDE.md`, repo conventions, GitHub Actions setup

### Teammate A — Sleep + HealthKit bridge + Streaks + Feed + Profiles
- Tables: `sleep_posts`, `sleep_stages`, `streaks`
- API: `/api/sleep`, `/api/healthkit/import`, `/api/users/:id`
- UI: feed tab + post-sleep modal + profile page
- HealthKit bridge implementation (reads `docs/healthkit-research.md`)
- **Silver nontrivial piece**: streaks

### Teammate B — Chat + Reactions + Realtime infra + Visual polish
- Tables: `messages`, `reactions`
- API: `/api/groups/:id/messages*`, `/api/sleep/:id/react`
- UI: chat tab + reactions UI + realtime subscription wiring (shared across all tabs)
- Visual design pass: type scale, color palette, mobile breakpoints

### Shared
- Tests + CI: each owner writes tests for their slice
- README: Micah drafts, all three review

**Standing meetings**: 15 min twice a week (per PDF). Shared chat for blockers.

## 10. Open questions to resolve in week 1

1. **HealthKit bridge path** — Teammate A picks one of: Apple Shortcuts, third-party broker (Terra/Vital/Rook), manual XML export, native iOS companion. Research doc at `docs/healthkit-research.md`. The schema is source-agnostic; only the import endpoint shape changes.
2. **Social model revisit** — Working default is closed groups with invite codes. If the team wants friends-graph instead, we revisit before week 2; after that it's too expensive to change.
3. **Visual identity** — Color palette, type scale, vibe. Teammate B drives. Need a decision by end of week 1 so styling doesn't get bolted on at week 3.
4. **Project name confirmation** — "synzoia" is the working name. Lock in the GitHub org/repo URL with the team.

## 11. Out of scope

Explicitly NOT building in v1:
- Friends graph (groups only)
- Competitions as state machine (rolling leaderboards only)
- Push notifications (realtime while on-page only)
- Comments / threaded discussion (reactions only)
- Photo uploads / avatars (URL field exists but no upload UI)
- Web push, email digests, SMS reminders
- Multi-group cross-posting (one post → one group)
- Admin tooling / moderation
- Native iOS app (web only; iOS companion is one HealthKit option for Teammate A)
- Analytics dashboard beyond what's on the profile page
