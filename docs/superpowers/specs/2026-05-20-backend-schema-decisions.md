# Backend schema design decisions — sleep + crews

**Date**: 2026-05-20
**Author**: Max
**Migration**: `backend/migrations/0001_initial.sql`
**Status**: Proposed (PR for team review)

This document captures the *why* behind every design choice in the initial backend schema. It's organized table-by-table, then cross-cutting concerns, then deferred work.

---

## 0. Context

The frontend was built first (placeholder UI in `frontend/src/pages/`). My job is to design a backend schema that:

1. **Adheres strictly to what Micah's UI already exposes.** No speculative columns for hypothetical features.
2. **Documents every column** so the professor can see deliberate thinking (per the Final Project PDF's "design decisions" README requirement).
3. **Leaves clean seams** for tables/features Micah hasn't built UI for yet (chat, reactions) and for v2 ideas we deliberately deferred.

What Micah's UI currently exposes (read from frontend code, not assumed):

| Page | Fields shown / inputs taken |
|---|---|
| `Auth.tsx` (sign-up) | email, password, display_name |
| `Settings.tsx` | display_name, timezone |
| `Crews.tsx` | "Create a crew" + "Join with code" |
| `CrewDetail.tsx` | crew name, tabs (feed / leaderboard / chat — chat shows "coming soon") |
| `PostSleep.tsx` | bedtime, wake_time, quality_score (1-100), note |
| `UserProfile.tsx` | display name, current + longest streak, recent posts |

Everything below traces back to one of those rows.

---

## 1. Scope

**In scope tonight (5 tables):**

| Table | Purpose | Maps to UI |
|---|---|---|
| `profiles` | User identity beyond `auth.users` | Auth signup, Settings |
| `groups` | A "crew" — small accountability group | Crews page |
| `memberships` | Many-to-many user-↔-crew | Crews list, feed visibility |
| `sleep_posts` | One row per night of sleep per user | PostSleep, feed, leaderboard, profile |
| `streaks` | Materialized current + longest streak per user | UserProfile "Streaks" section |

**Deferred to next backend session (UI placeholders exist, real UI doesn't):**

- `messages` — chat tab on `CrewDetail` says "coming soon"
- `reactions` — feed is empty placeholder, no reaction UI yet

**Deferred to v2 (see `docs/v2-roadmap.md` for the full list):**

- Sleep stages (REM/Core/Deep/Awake)
- ~~`source` field (manual vs HealthKit vs Whoop)~~ — *landed in v1 via migration 0002*
- `avatar_url`, `bio`, `sleep_goal_minutes` on profiles
- Group rotation / matchmaking / achievement-gating
- Multi-category health data (heart rate, workouts, food, weight)
- HealthKit + tracker integrations
- Privacy toggles, per-post visibility, app-level encryption
- Push notifications, email digests
- GitHub-style sleep heatmap on profile

---

## 2. Table-by-table decisions

### 2.1 `profiles`

```
id            UUID PK → auth.users(id) ON DELETE CASCADE
display_name  text NOT NULL (1-60 chars)
timezone      text NOT NULL, default 'America/Chicago'
created_at    timestamp NOT NULL default now()
updated_at    timestamp NOT NULL default now()
```

**Why a separate `profiles` table at all?**
Supabase Auth provides `auth.users` with email, password hash, and a UUID `id`. But we don't *own* `auth.users` — we can't add app-specific columns (timezone, display_name) to it without coupling to Supabase's schema. A separate `profiles` table linked 1:1 by `id` gives us a stable target for foreign keys that survives auth-provider changes.

**Why `display_name` instead of `username`?**
v1 has no @-mention feature and no URL-slug requirements. `display_name` covers what Micah's Auth and Settings UIs need. A separate `username` column adds complexity (unique constraint, regex validation) for zero current benefit. Easy to add later via migration.

**Why `timezone` is mandatory:**
Both `night_of` bucketing (sleep posts) and streak computation depend on the user's timezone. Without it, "what day did this sleep happen on?" is ambiguous. Defaulting to `America/Chicago` because that's our cohort.

**Why no `avatar_url`, `bio`, `sleep_goal_minutes`?**
None appear in Micah's Settings UI. Adding columns no feature uses is dead weight. Deferred to v2-roadmap.

---

### 2.2 `groups`

```
id           UUID PK
name         text NOT NULL (1-60 chars)
invite_code  text NOT NULL UNIQUE (exactly 8 chars)
created_at   timestamp NOT NULL default now()
```

**Why invite codes instead of email invitations?**
Email invites require email-sending infrastructure (SendGrid, deliverability config). Invite codes are a single column on the table and a "Join with code" UI element — which Micah already built. Zero infrastructure cost.

**Why 8 characters alphanumeric?**
`36^8 ≈ 2.8 × 10^12` possible codes — no realistic collision risk for a class project even at university scale. Short enough to text/share verbally without being annoying.

**Why no `created_by` column?**
No UI surfaces who created a crew. There's no admin/owner distinction in CrewDetail.tsx. If we need owner permissions later, `memberships` can carry a `role` column then — cleaner than denormalizing creator info onto `groups`.

**Why no `description`, `cover_image`, `is_public`?**
None in Micah's UI. YAGNI.

---

### 2.3 `memberships`

```
group_id    UUID NOT NULL → groups(id)   ON DELETE CASCADE
user_id     UUID NOT NULL → profiles(id) ON DELETE CASCADE
joined_at   timestamp NOT NULL default now()
PRIMARY KEY (group_id, user_id)
```

**Why a composite primary key instead of a synthetic `id`?**
The pair `(group_id, user_id)` *is* the identity of a membership row. A separate `id` would be redundant. Composite PK also enforces "user can only join a crew once" automatically — no extra unique constraint needed.

**Why no `role` column?**
No UI distinguishes owners from members. Add later if/when admin features get built.

**Why two `ON DELETE CASCADE`s?**
If a crew is deleted, its memberships are meaningless. If a user is deleted, their memberships are meaningless. CASCADE in both directions keeps the join table clean.

**Why the index on `user_id`?**
The Crews page query is *"list every crew this user belongs to"* — i.e., `WHERE user_id = ?`. Without the index, Postgres would scan all memberships. The primary key indexes `(group_id, user_id)` (left-prefix rule), so a separate `user_id` index is required.

---

### 2.4 `sleep_posts`

```
id              UUID PK
user_id         UUID NOT NULL → profiles(id) ON DELETE CASCADE
night_of        date NOT NULL
bedtime         timestamptz NOT NULL
wake_time       timestamptz NOT NULL, CHECK > bedtime
duration_min    integer NOT NULL, CHECK 1-1440
quality_score   integer NULL, CHECK 1-100
note            text NULL, CHECK char_length ≤ 280
created_at      timestamp NOT NULL default now()
UNIQUE (user_id, night_of)
```

This is the table that the most thought went into.

**Why posts are user-scoped, not crew-scoped:**
A sleep is a fact about your body. You only sleep once per night. Making users post the same sleep separately to each of their crews:
1. Defeats accountability (you could post "honest" data to one crew and a filtered version to another)
2. Creates data duplication
3. Doesn't match the mental model — sleep isn't audience-targeted content

Instead: a sleep post belongs to the user. Feed visibility for a crew is computed at query time via a join through `memberships`. The feed query for a crew looks like:

```sql
SELECT sp.*
FROM sleep_posts sp
JOIN memberships m ON m.user_id = sp.user_id
WHERE m.group_id = $crew_id
ORDER BY sp.night_of DESC, sp.created_at DESC;
```

**Why `night_of` is stored explicitly, not derived from bedtime:**
A sleep that starts at 1am Saturday and ends at 8am Saturday should "belong" to Friday night, not Saturday. Re-deriving this rule on every query is fiddly (timezones, late-night posts, naps). Computing once on insert and storing as a date column makes every downstream query trivial:

```sql
-- "this week's sleep posts for crew X"
WHERE sp.night_of BETWEEN $start AND $end
```

The rule: `night_of = (wake_time AT TIME ZONE user.timezone)::date - 1 day`. Naps are explicitly out of scope in v1.

**Why `duration_min` is stored, not computed from `bedtime`/`wake_time`:**
Today, `duration_min = wake_time - bedtime` for manual entries. But when HealthKit lands in v2 and we add sleep stages, `duration_min` will equal `rem + core + deep` (excluding time awake mid-night), which is NOT the same as `wake_time - bedtime`. Storing it explicitly future-proofs the leaderboard query without breaking when v2 ships.

**Why `quality_score` is nullable:**
Micah's UI shows the field but doesn't require it. A user can post without rating. Cross-tracker comparability is imperfect (Whoop's 85 ≠ Oura's 85), so the leaderboard probably shouldn't rank on it — but the field exists for display and personal tracking.

**Why `note` is capped at 280 chars:**
Twitter-length. Forces brevity, keeps the feed scannable, matches the "quick social post" vibe (Strava's activity-note pattern). Long-form journaling can be a v2 feature.

**Why `UNIQUE (user_id, night_of)` (now a partial unique index — see migration 0002):**
Prevents double-posting for the same night. Without this, a user could post their sleep three times and inflate the leaderboard. Enforced at the DB level because the API alone can't be trusted (race conditions, retries, bugs). As of migration 0002, the constraint is a *partial* unique index `WHERE deleted_at IS NULL` so users can re-post after a soft delete.

**Why no sleep stages:** No UI input. Add when HealthKit bridge lands.

**`source`, `updated_at`, `deleted_at` (added in migration 0002):** See §5 — these resolved the v1 open questions on tracker badges and edit/delete UX.

**Why the index on `(user_id, night_of desc)`:**
Two hot queries:
1. Feed for a crew: `JOIN memberships ... WHERE m.group_id = ?` — uses `user_id` as the join key.
2. Profile page: "show me my recent sleep posts" — `WHERE user_id = ? ORDER BY night_of DESC LIMIT 20`.

Both hit `user_id`; the second benefits from `night_of DESC` being part of the index. One composite index serves both.

---

### 2.5 `streaks`

```
user_id         UUID PK → profiles(id) ON DELETE CASCADE
current_streak  integer NOT NULL default 0
longest_streak  integer NOT NULL default 0
last_night_of   date NULL
updated_at      timestamp NOT NULL default now()
```

**Why materialized (not computed on read):**
A streak query has to walk a user's sleep posts ordered by `night_of`, count consecutive dates, detect gaps, handle "today is a grace day," and bucket everything in the user's IANA timezone. Doing that on every profile load and leaderboard render gets expensive fast.

Materialization makes reads trivial (`SELECT * FROM streaks WHERE user_id = ?`) and concentrates all the complexity in one place: the `recompute_streak(user_id)` function that runs in the same transaction as a `sleep_posts INSERT`.

**This is the silver-tier "nontrivial logic" piece per the Final Project PDF.** The complexity isn't in the table — it's in the update function (timezone math, DST, grace days, gap detection). Lives in `backend/app/services/streaks.py` (TBD).

**Why `last_night_of` is nullable:**
A brand-new user has never posted. Streak = 0, last_night_of = NULL. Distinguishes "never posted" from "posted but streak is 0 because they broke it."

**Why the `current_streak ≤ longest_streak` CHECK:**
Database-level invariant. Even if the update logic has a bug, the DB will reject any state where current exceeds longest. Cheap defense-in-depth.

---

## 3. Cross-cutting decisions

### 3.1 UUIDs everywhere

Every primary key is a UUID. Reasons:
- They're not guessable (no information leak from a sequential ID)
- They're generatable client-side without a DB round trip
- They make eventual federation/sync stories easier
- Cost: 16 bytes per ID vs 8 for a bigint. Negligible at our scale.

### 3.2 `timestamptz` everywhere, not `timestamp`

Every timestamp uses `timestamptz`. Postgres stores it as UTC and converts on read. Without it, "Max posted at 11pm" is meaningless across timezones.

### 3.3 Constraints at the DB level, not the API

Every length cap (`char_length ≤ N`), range check (`BETWEEN 1 AND 1440`), and uniqueness constraint is enforced at the database. Per the project CLAUDE.md and the lectures (2.2 Databases): the DB is the last line of defense. Pydantic validates shape; the DB validates invariants.

### 3.4 Foreign keys with explicit `ON DELETE` behavior

Every foreign key in this schema has an explicit `ON DELETE` clause. Most use `CASCADE` — when a parent is deleted, owned children are deleted too. This prevents orphan rows pointing at non-existent users / crews.

### 3.5 Indexes are deliberate, not exhaustive

Three indexes total:
1. `memberships(user_id)` — "what crews am I in?"
2. `sleep_posts(user_id, night_of desc)` — feed + profile hot path
3. Primary keys (automatic) — `profiles(id)`, `groups(id)`, `sleep_posts(id)`, `streaks(user_id)`, `memberships(group_id, user_id)`, `groups.invite_code` (unique implies index)

Per the project CLAUDE.md: "Three deliberate indexes, that's it." Add more only when measured.

### 3.6 No `updated_at` on tables that aren't edited

`groups`, `memberships`, `sleep_posts` have no `updated_at` column in v1 because the UI doesn't expose edit flows for them. `profiles` and `streaks` do — both have features that mutate them (Settings page, streak recomputation).

---

## 4. What's not in this migration (and why)

### Tables deferred to the next backend session:
- **`messages`** — Chat tab on CrewDetail is "coming soon." When Micah builds the chat UI, this table gets added.
- **`reactions`** — No reaction UI on feed cards yet. When Micah builds reaction buttons, this table gets added.

### Tables deferred to v2:
See `docs/v2-roadmap.md` for the full list. Anything beyond v1 lives there.

### Things this migration deliberately does NOT include:
- **Row-Level Security policies.** Only needed if the frontend subscribes directly to Supabase Realtime. Until that's the architecture, FastAPI's auth checks are sufficient. Adding RLS later is a non-breaking migration.
- **Triggers.** All cross-table consistency (e.g., updating `streaks` on `sleep_posts` INSERT) runs in application code inside a transaction. Triggers are harder to test and debug; we'll only add them if measured performance requires it.
- **Materialized views.** None needed at our scale. The leaderboard query runs against `sleep_posts` directly with the indexes above.

---

## 5. Open questions for Micah / next session

These are explicit asks for Micah / the team before we go further:

1. ~~**`quality_score` field — keep it?**~~ **Resolved 2026-05-21 (migration 0002):** column stays, used for **personal display only** — never as a leaderboard input. Locked in via `COMMENT ON COLUMN sleep_posts.quality_score`.
2. ~~**Editing / deleting sleep posts**~~ **Resolved 2026-05-21 (migration 0002):** added `updated_at` (maintained by a `touch_updated_at` trigger) and `deleted_at` for soft delete. Replaced `UNIQUE (user_id, night_of)` with a **partial** unique index `WHERE deleted_at IS NULL` so users can re-post after deletion.
3. **Account deletion flow** — Right now `ON DELETE CASCADE` from `profiles` removes all sleep posts, memberships, and streaks. Is that the intended behavior, or do we want soft delete + retention? *(Still open — explicitly left alone for now.)*
4. ~~**`source` field on sleep_posts**~~ **Resolved 2026-05-21 (migration 0002):** added `source text NOT NULL default 'manual'` with `CHECK source IN ('manual', 'apple_health', 'whoop', 'oura', 'fitbit', 'garmin')`. New trackers = 1-line CHECK update.

---

## 6. Frontend suggestions

Things I considered but didn't build into the schema because they're not in Micah's UI. Adding them is cheap once UI exists:

- **Sleep goal + weekly progress bar.** A single nullable `sleep_goal_minutes` column on `profiles` + a frontend bar showing this week's total vs goal × 7. Engaging personal-feedback feature.
- ~~**Strava-style data-source badges.**~~ **Resolved 2026-05-21:** `source` column added in migration 0002; the dashboard feed now renders a small "via Apple Health" / "via Whoop" badge for non-manual entries.
- **Profile bio.** Twitter-style 160-char self-description. Makes profile pages feel less like stat sheets.
- **GitHub-style sleep heatmap.** Calendar grid on profile page showing which nights the user posted, color-coded by quality/duration. High-signal visualization, ~30 lines of frontend work, zero new schema.
- **Profile photos.** `avatar_url` column on profiles, points at Supabase Storage. Avatar circles next to feed posts.

If any of these get into the v1 UI, the corresponding schema additions are 1-line migrations.
