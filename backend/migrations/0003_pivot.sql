-- ============================================================================
-- 0003_pivot.sql
-- ============================================================================
-- Product pivot decided at the 5/23/2026 team meeting.
--
-- WHAT'S CHANGING:
--
--   The original "private crews" social model is being replaced with a
--   universal-feed model. Users authenticate via a server-issued token they
--   paste into an iOS Shortcut (no Supabase Auth, no email/password).
--   Activity (sleep, steps, workouts) is posted by the Shortcut and shown
--   in one global feed.
--
-- TABLES DROPPED (no longer part of the product):
--
--   - groups         — no more "crews"
--   - memberships    — no crews to be a member of
--   - streaks        — out of scope for the new model
--   - sleep_posts    — dropped here because its FK depends on profiles.id
--                      whose type is changing from UUID to BIGINT. Will be
--                      recreated in a follow-up migration alongside the
--                      other activity tables (steps, workouts) for the new
--                      universal-feed model.
--   - profiles       — dropped and recreated with a completely new shape
--                      (UUID -> BIGINT id, plus token, plus username,
--                      drops display_name, timezone, avatar_url, etc.).
--
-- TABLES NOT TOUCHED:
--
--   None — all five v1 tables are being dropped. Data loss is acceptable
--   because all tables are empty (verified before applying).
--
-- WHY DROP-AND-RECREATE INSTEAD OF ALTER:
--
--   profiles.id is changing type (UUID -> BIGINT). Postgres allows column
--   type changes, but doing so when other tables FK to it is painful
--   (drop FK -> alter column -> recreate FK -> backfill -> ...). Tables
--   are empty, so drop-and-recreate is simpler and equivalent.
--
-- DROP ORDER:
--
--   Respect foreign keys: drop children before parents.
--     streaks      -> FK to profiles
--     memberships  -> FK to profiles + groups
--     sleep_posts  -> FK to profiles
--     groups       -> referenced by memberships (drop after memberships)
--     profiles     -> referenced by all of the above (drop last)
--
-- Design rationale lives in:
--   docs/superpowers/specs/2026-05-23-backend-pivot-design.md
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Drop everything from the old crews model.
-- ----------------------------------------------------------------------------
drop trigger if exists sleep_posts_touch_updated_at on sleep_posts;

drop table if exists streaks;
drop table if exists memberships;
drop table if exists sleep_posts;
drop table if exists groups;
drop table if exists profiles;

-- touch_updated_at() is a generic helper from migration 0002. Keep it —
-- new tables will likely reuse it.


-- ----------------------------------------------------------------------------
-- profiles (new shape)
-- ----------------------------------------------------------------------------
-- One row per signed-up user. No Supabase Auth dependency; the server
-- issues a token at signup that the user pastes into their iOS Shortcut.
--
-- Columns:
--   id          BIGSERIAL — auto-incrementing internal id. Not exposed in
--                            URLs (we use username for that), so a leaky
--                            sequential id is fine and saves bytes vs UUID.
--   username    TEXT      — the public identity. Unique. Length-capped to
--                            match what the website's signup form will
--                            accept; character set kept permissive for now
--                            and tightened later if needed.
--   token       TEXT      — secret API key the Shortcut sends with every
--                            request. Unique, NOT NULL, length-capped to
--                            prevent abusive submissions.
--   join_date   TIMESTAMPTZ — when the profile was created.
--
-- Intentionally NOT included (resolved at 5/23 meeting):
--   timezone        — Shortcut will send timezone on each post that needs
--                     it; no need to store per-user.
--   display_name    — username covers it for v1.
--   avatar_url, bio — no UI.
--   updated_at      — profiles aren't editable in v1's UI; add later if
--                     editing lands.
-- ----------------------------------------------------------------------------
create table profiles (
    id          bigserial   primary key,
    username    text        not null unique
                            check (char_length(username) between 1 and 30),
    token       text        not null unique
                            check (char_length(token) between 16 and 128),
    join_date   timestamptz not null default now()
);


-- ============================================================================
-- end 0003_pivot.sql
-- ============================================================================
