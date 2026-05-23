# Backend pivot — universal feed + token auth

**Date**: 2026-05-23
**Author**: Max
**Migration**: `backend/migrations/0003_pivot.sql`
**Status**: Proposed (PR for team review — DO NOT APPLY to Supabase until reviewed)
**Supersedes (partially)**: `2026-05-20-backend-schema-decisions.md`

This doc captures the *what* and *why* of the schema pivot decided at the 5/23/2026 team meeting. It only covers the **profiles** rebuild — `sleep_posts`, `workouts`, `steps`, and the rest of the new activity tables will be designed in follow-up migrations once `profiles` is locked in.

---

## 0. What's actually changing

### Old model (v1, the one that just shipped via PRs #7 + #11)

A small private-group sleep tracker. Users sign in with email + password via Supabase Auth, join "crews" of 2-5 friends via invite codes, post nightly sleep, see each other's posts in a per-crew feed, and the app tracks streaks per user.

### New model (5/23 meeting)

A universal-feed activity app. Users sign up by picking a username on the website, the server issues them a token, they paste that token into an iOS Shortcut, and the Shortcut posts their activity (sleep, steps, workouts) to the backend. Everyone sees one global feed of everyone's activity — no crews, no memberships.

---

## 1. Tables being removed

| Table | Why it's being dropped |
|---|---|
| `groups` | No more crews — there's nothing to group people into |
| `memberships` | No groups means no membership joins |
| `streaks` | Decided out of scope at the 5/23 meeting |
| `sleep_posts` | Not philosophically dropped, but technically must be — its FK to `profiles.id` breaks when that column's type changes. Will be **recreated** in the next migration alongside `steps` and `workouts` for the universal-feed model. |
| `profiles` (old shape) | Being rebuilt with a fundamentally different schema (no Supabase Auth dependency, BIGINT id instead of UUID) |

**Data loss is acceptable:** all five tables are currently empty in Supabase. No production data exists to migrate.

---

## 2. The new `profiles` table

```sql
profiles
├── id          bigserial PRIMARY KEY
├── username    text NOT NULL UNIQUE (1-30 chars)
├── token       text NOT NULL UNIQUE (16-128 chars)
└── join_date   timestamptz NOT NULL DEFAULT now()
```

### Per-column rationale

**`id` — BIGSERIAL instead of UUID.**
The old profiles.id was UUID to match `auth.users.id` from Supabase Auth. Since we're dropping Supabase Auth, that constraint is gone. URLs in the new product will use `username` (e.g. `/u/max`), not numeric ids, so a sequential id leaks no useful information. BIGINT is 8 bytes vs UUID's 16, half the index size, slightly faster joins. No downside for our scale.

**`username` — public identity.**
Replaces the old `display_name`. Unique because users will be referenced by username in URLs and the feed. Length-capped at 30 to keep feed rendering predictable.

**`token` — secret for iOS Shortcut auth.**
This is the core of the new auth model. When the user signs up, the server generates a random token (e.g. 32-64 hex chars) and shows it to the user. The user pastes it into their iOS Shortcut. From then on, every request the Shortcut makes includes that token in a header (`Authorization: Bearer <token>` or `X-Synzoia-Token: <token>`), and the server looks up "who has this token?" → that's the user.

Why this and not Supabase Auth?
- The product's main interface is an iOS Shortcut, not a browser. Email/password flows make no sense there.
- Shortcuts can hold a single static string in a variable. Tokens fit that constraint perfectly.
- Removes the entire Supabase Auth dependency (JWT verification, JWKs, etc.) — simpler backend code.

**`join_date` — when the profile was created.**
Equivalent to `created_at`; renamed because that's what the user sketched at the meeting.

### Per-column rationale for what's NOT here

**No `timezone`.**
The old design stored timezone on the user because the leaderboard/streak windowing needed it. Without streaks, timezone is only needed for `night_of` bucketing on sleep posts — and the iOS Shortcut can send the timezone with each post. That keeps `profiles` smaller and lets users travel without their data being mis-bucketed.

**No `display_name` separate from `username`.**
v1 doesn't have a "@-mention" feature where username and display name would diverge. Adding both is two columns where one will do.

**No `avatar_url`, `bio`, `email`, `phone`.**
None appear in the new product flow described at the meeting.

**No `updated_at`.**
The new model doesn't expose profile editing in v1. If it lands later, add the column in a one-line migration.

---

## 3. Token security notes

Things this migration deliberately does NOT do, but should be considered before going to production:

1. **Tokens stored in plaintext.** The standard pattern is to store a hash (e.g. SHA-256) of the token and compare against that. For a class project at our scale this is acceptable, but if synzoia ever scales we should switch to hashed storage.
2. **No token rotation endpoint.** Users can't generate a new token if their old one leaks. Worth adding when the website has an account-settings page.
3. **No token expiry.** Tokens are valid forever once issued. Fine for v1.

These trade-offs belong in `v2-roadmap.md` once this migration is approved.

---

## 4. What's coming in follow-up migrations

The next backend session will design the activity tables for the new feed:

- **`sleep_posts`** — rebuilt with `user_id BIGINT` (matching the new `profiles.id`). Probably keeps the bedtime/wake_time/night_of/quality_score/note structure from before, possibly with the `source`/`updated_at`/`deleted_at` extensions from 0002. To be confirmed during design.
- **`steps`** — track daily step counts so the feed can post "milestone" events (1000, 5000, 10000 steps).
- **`workouts`** — type, duration, distance, etc. Feed posts go up after a workout.
- **`food`** (optional) — meals/macros if we have time.

Each gets its own migration + design doc. None of those tables are in scope for this PR — this PR is just the pivot foundation: drop the old, rebuild `profiles`.

---

## 5. What's NOT changing in this PR

To keep the blast radius tight, this migration deliberately doesn't touch:

- The Supabase project itself (only the schema inside it).
- Frontend code. Micah's `DbExplorer.tsx` and `/api/health/db` endpoint will need to be updated to know about the new table list — that's a follow-up task, not part of this migration.
- The `touch_updated_at()` PL/pgSQL helper from migration 0002 — kept around because the new activity tables will likely reuse it.
- CLAUDE.md, README.md, or the old `2026-05-20-backend-schema-decisions.md` — those stay as historical record. The old design isn't *wrong*, it's just *superseded*. When the dust settles, we should update CLAUDE.md so future sessions don't reference the dead tables.

---

## 6. Action plan after this PR merges

1. Update `backend/app/main.py` to remove dropped tables from the `_TABLES` tuple used by `/api/health/db` and `/api/db/dump`.
2. Update `frontend/src/pages/DbExplorer.tsx` to reflect the new table list.
3. Apply this migration to the live Supabase project (paste `0003_pivot.sql` into SQL Editor, run).
4. Design the next migration (`0004_activity_tables.sql`) for sleep + steps + workouts.

---

## 7. Open questions

These deserve a quick team check before applying to Supabase:

1. **Token format.** Should I issue tokens as 32 hex chars (`a3f2x9kp...`), URL-safe base64 (`AbC-123_...`), or with a recognizable prefix (`syn_a3f2x9kp...`)? The CHECK constraint allows 16-128 chars — generous enough for any of these. Pick at app-code time.

2. **Username character set.** Currently no regex check beyond length. Should we restrict to `[a-zA-Z0-9_]` like most apps, or stay permissive? Restricting later requires backfilling old rows.

3. **Should we keep migrations 0001 + 0002 in git, or squash them away?** My vote: keep them as history. The repo tells the story of how the project evolved.
