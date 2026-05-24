-- ============================================================================
-- 0005_posts.sql
-- ============================================================================
-- Adds the `posts` table — the universal activity feed.
--
-- A post is a "feed event": user X did activity of type Y at time Z. The
-- actual payload (step count, sleep duration, workout distance, etc.)
-- lives in the type-specific tables (steps, sleep, workouts) — `posts`
-- is just the chronological event log that powers the feed.
--
-- Columns:
--   id         BIGSERIAL  primary key
--   user_id    BIGINT     FK to profiles(id), ON DELETE CASCADE
--   username   TEXT       denormalized copy of profiles.username so feed
--                          reads don't need a JOIN. Populated server-side
--                          at insert time from the token-resolved user.
--                          Documented trade-off: if a user ever renames,
--                          old posts keep the old username (acceptable
--                          for v1; usernames don't change in the UI).
--   type       TEXT       activity kind: 'sleep' | 'steps' | 'workout'.
--                          CHECK-constrained at the DB level so a code
--                          bug or stray client can't insert a bogus type.
--   timestamp  TIMESTAMP  when the activity happened (sent by the client;
--                          NOT created_at — that would record server
--                          insertion time, which is different).
--
-- Indexes:
--   - posts (timestamp DESC) — the hot feed query is "newest first"
--   - posts (user_id, timestamp DESC) — per-user feed query
-- ============================================================================

create table posts (
    id         bigserial   primary key,
    user_id    bigint      not null references profiles(id) on delete cascade,
    username   text        not null,
    type       text        not null check (type in ('sleep', 'steps', 'workout')),
    timestamp  timestamp   not null
);

create index posts_timestamp_idx
    on posts (timestamp desc);

create index posts_user_timestamp_idx
    on posts (user_id, timestamp desc);
