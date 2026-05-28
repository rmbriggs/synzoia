-- ============================================================================
-- 0008_sleep.sql
-- ============================================================================
-- Adds the `sleep` table — one row per user per night.
--
-- Shape mirrors `steps` where it makes sense: BIGSERIAL id, BIGINT
-- user_id FK to profiles with ON DELETE CASCADE, naive TIMESTAMP for
-- bedtime/wake_time (iOS Shortcut writes UTC; the service converts to
-- CT for date-bucketing, same pattern as steps).
--
-- Unlike steps, sleep is one row per night (not many snapshots per
-- day). The `night_of` column is the calendar date the sleep "counts
-- for" — typically the date the user went to bed in their local time.
-- The service computes it on insert as (wake_time CT date − 1 day),
-- so a 2 AM bedtime / 9 AM wake still buckets to the prior night.
--
-- Apple Health provides per-stage breakdowns on newer Apple Watches
-- (REM / Core / Deep / Awake minutes). Each is nullable so manual
-- entries and older devices still work.
--
-- Naps are out of scope for v1 — the iOS Shortcut filters them out
-- before posting, so each row here is a single overnight session.
--
-- Columns:
--   id            BIGSERIAL  primary key
--   user_id       BIGINT     FK to profiles(id); whose sleep this is
--   bedtime       TIMESTAMP  when they got in bed (UTC; CT-bucketed in
--                            service queries)
--   wake_time     TIMESTAMP  when they got out of bed; must be > bedtime
--   duration_min  INTEGER    actual minutes asleep — Apple Health
--                            excludes the "awake during sleep" time
--   rem_minutes   INTEGER    nullable per-stage breakdowns
--   core_minutes  INTEGER
--   deep_minutes  INTEGER
--   awake_minutes INTEGER
--   night_of      DATE       computed by service on insert as
--                            (wake_time CT date − 1 day)
--   created_at    TIMESTAMP  when the row was inserted
--
-- Constraints:
--   - UNIQUE (user_id, night_of)  — one sleep row per user per night;
--                                    the Shortcut can't double-post the
--                                    same night
--   - wake_time > bedtime         — sanity
--   - duration_min in [0, 1440]   — 0 to 24 hours
--   - per-stage CHECKs            — null OR non-negative
--
-- RLS:
--   - Enabled at the bottom, matching the policy in 0006_enable_rls.sql.
--     FastAPI connects as `postgres` (BYPASSRLS); the anon/authenticated
--     roles are denied access to all rows. No POLICY statements yet.
-- ============================================================================

create table sleep (
    id            bigserial primary key,
    user_id       bigint    not null references profiles(id) on delete cascade,
    bedtime       timestamp not null,
    wake_time     timestamp not null,
    duration_min  integer   not null check (duration_min between 0 and 1440),
    rem_minutes   integer            check (rem_minutes   is null or rem_minutes   >= 0),
    core_minutes  integer            check (core_minutes  is null or core_minutes  >= 0),
    deep_minutes  integer            check (deep_minutes  is null or deep_minutes  >= 0),
    awake_minutes integer            check (awake_minutes is null or awake_minutes >= 0),
    night_of      date      not null,
    created_at    timestamp not null default now(),
    unique (user_id, night_of),
    check (wake_time > bedtime)
);

-- Match 0006: deny anon/authenticated roles by default. FastAPI's
-- BYPASSRLS-capable role can still read/write freely.
alter table public.sleep enable row level security;
