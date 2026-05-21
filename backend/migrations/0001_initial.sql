-- ============================================================================
-- 0001_initial.sql
-- ============================================================================
-- Initial schema for synzoia: a private-group sleep-tracking app.
--
-- This migration creates the five tables needed to support Micah's current
-- frontend UI:
--   1. profiles      — user identity beyond what auth.users provides
--   2. groups        — the "crews" themselves
--   3. memberships   — many-to-many between users and crews
--   4. sleep_posts   — one row per night of sleep per user
--   5. streaks       — materialized current + longest streak per user
--
-- Tables explicitly NOT included in this migration (deferred):
--   - messages    — chat tab is "coming soon" in the UI
--   - reactions   — no UI element yet
--
-- Design rationale lives in:
--   docs/superpowers/specs/2026-05-20-backend-schema-decisions.md
--
-- Apply with:
--   psql $DATABASE_URL -f backend/migrations/0001_initial.sql
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. profiles
-- ----------------------------------------------------------------------------
-- One row per signed-up user. Mirrors auth.users (managed by Supabase Auth)
-- with the app-specific fields we own. Linked 1:1 by id.
--
-- Why a separate table from auth.users:
--   We don't own auth.users (Supabase manages it). We need our own columns
--   (display_name, timezone) and we want a stable target for foreign keys
--   that survives auth-provider changes.
-- ----------------------------------------------------------------------------
create table profiles (
    id              uuid primary key references auth.users(id) on delete cascade,
    display_name    text        not null check (char_length(display_name) between 1 and 60),
    timezone        text        not null default 'America/Chicago',
                                -- IANA timezone identifier; critical for streak
                                -- and leaderboard date-bucketing per user
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);


-- ----------------------------------------------------------------------------
-- 2. groups
-- ----------------------------------------------------------------------------
-- A "crew" — a small private accountability group.
--
-- Micah's UI exposes: "Create a crew" + "Join with code" — so we need name
-- and invite_code at minimum.
--
-- created_by intentionally omitted: no UI surfaces it, and memberships
-- already tracks the user-↔-crew relationship.
-- ----------------------------------------------------------------------------
create table groups (
    id              uuid        primary key default gen_random_uuid(),
    name            text        not null check (char_length(name) between 1 and 60),
    invite_code     text        not null unique check (char_length(invite_code) = 8),
                                -- 8-char alphanumeric, generated app-side;
                                -- ~218 trillion combos — no realistic collision risk
    created_at      timestamptz not null default now()
);


-- ----------------------------------------------------------------------------
-- 3. memberships
-- ----------------------------------------------------------------------------
-- Many-to-many link between users and crews.
--
-- Composite primary key (group_id, user_id) enforces "a user can only join
-- a given crew once" automatically. No need for a separate id column or a
-- separate unique constraint.
--
-- ON DELETE CASCADE in both directions: if a crew is deleted, its memberships
-- vanish; if a user is deleted, their memberships vanish.
--
-- role column intentionally omitted: no UI surfaces an owner/member
-- distinction in v1.
-- ----------------------------------------------------------------------------
create table memberships (
    group_id        uuid        not null references groups(id)   on delete cascade,
    user_id         uuid        not null references profiles(id) on delete cascade,
    joined_at       timestamptz not null default now(),
    primary key (group_id, user_id)
);

-- Index for "show me all crews this user belongs to" — hit on every
-- /crews page load.
create index memberships_user_id_idx on memberships (user_id);


-- ----------------------------------------------------------------------------
-- 4. sleep_posts
-- ----------------------------------------------------------------------------
-- One row per night of sleep per user.
--
-- Scoping: posts are user-scoped, NOT crew-scoped. A single post is visible
-- in every crew the user belongs to (visibility computed at query time via
-- a join through memberships). This matches the "accountability" mental
-- model — you only sleep once per night and your crews see the same data.
--
-- night_of: the date this sleep "counts for." Computed once at insert as
-- (wake_time::date - 1 day) so late-night-to-morning sleeps bucket to the
-- prior day's night (e.g., bed at 1am, wake at 8am → night_of = yesterday).
-- Storing it explicitly avoids re-deriving from bedtime on every query.
--
-- duration_min: actual sleep time in minutes, computed by the backend on
-- insert. For manual entries, equals (wake_time - bedtime). When sleep stages
-- arrive in v2, will equal (rem + core + deep), not including time awake.
--
-- Columns intentionally omitted in v1 (see v2-roadmap.md):
--   - rem/core/deep/awake_minutes (sleep stages) — no UI input
--   - source — no UI input; always 'manual' in v1
-- ----------------------------------------------------------------------------
create table sleep_posts (
    id              uuid        primary key default gen_random_uuid(),
    user_id         uuid        not null references profiles(id) on delete cascade,
    night_of        date        not null,
    bedtime         timestamptz not null,
    wake_time       timestamptz not null,
    duration_min    integer     not null check (duration_min between 1 and 1440),
                                -- 1 min to 24h sanity range
    quality_score   integer              check (quality_score between 1 and 100),
                                -- nullable: user may skip the quality field
    note            text                 check (char_length(note) <= 280),
                                -- nullable; Strava-style optional journal
    created_at      timestamptz not null default now(),

    -- A user can't post twice for the same night, enforced at the DB level.
    -- Prevents accidental double-counting in leaderboards/streaks.
    unique (user_id, night_of),

    -- wake_time must be after bedtime
    check (wake_time > bedtime)
);

-- Index for "give me all sleep posts from users in this crew, newest first"
-- — the hot path for feed rendering.
create index sleep_posts_user_night_idx on sleep_posts (user_id, night_of desc);


-- ----------------------------------------------------------------------------
-- 5. streaks
-- ----------------------------------------------------------------------------
-- Materialized current + longest streak per user.
--
-- Why materialized (not computed on read):
--   Streak computation requires walking sleep_posts ordered by night_of
--   and counting consecutive dates with gap detection in the user's
--   timezone. Expensive to run on every profile/leaderboard read. Cheap
--   to maintain incrementally: backend updates this row in the SAME
--   TRANSACTION as a sleep_posts insert.
--
-- This update logic is the silver-tier "nontrivial logic" piece — it has
-- to handle timezone bucketing, DST, the "today is a grace day" rule, and
-- gap detection. Lives in backend/app/services/streaks.py when that
-- exists.
-- ----------------------------------------------------------------------------
create table streaks (
    user_id         uuid        primary key references profiles(id) on delete cascade,
    current_streak  integer     not null default 0 check (current_streak  >= 0),
    longest_streak  integer     not null default 0 check (longest_streak  >= 0),
    last_night_of   date,
                                -- nullable: null means user has never posted;
                                -- when set, holds the night_of of their most
                                -- recent post (drives gap detection)
    updated_at      timestamptz not null default now(),

    -- Sanity invariant: current can never exceed longest
    check (current_streak <= longest_streak)
);


-- ============================================================================
-- end 0001_initial.sql
-- ============================================================================
