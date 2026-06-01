-- ============================================================================
-- 0010_workouts.sql
-- ============================================================================
-- Two tables that together model the workout half of the daily ingest:
--
--   runs            — one row per RUN event (distance + window + derived
--                     metrics). Strava-style: the iOS Shortcut posts every
--                     completed run; the server normalizes (merges sub-3-min
--                     gaps, drops pace outliers) before storing.
--
--   calorie_buckets — one row per hourly active-energy sample. Apple Health
--                     exports an active-energy time series; the Shortcut
--                     forwards each hourly bucket. Calories burned during a
--                     run are derived by PRORATING these buckets across the
--                     run's window — not stored directly on the run row's
--                     write path. Re-prorated whenever new buckets land.
--
-- Why two tables (and NOT a single `workouts` with a kind column):
--   - The calorie stream is hourly + continuous; a run is a discrete event
--     with a precise [start, end]. They have different upsert keys and
--     different access patterns. Cramming both into one row shape was the
--     first-pass mistake — calories aren't "a workout".
--   - Runs without overlapping bucket coverage carry calories_unavailable
--     so the UI can show "—" instead of "0 kcal".
--
-- Run lifecycle:
--   1. Shortcut POSTs the run shortly after it ends. status='provisional'
--      if captured_at - ended_at < 30 min, else 'final'.
--   2. The 1-hour calorie buckets covering that window land on the next
--      hour boundary. The service re-runs proration and updates the run's
--      `calories` + `calories_unavailable`.
--
-- Pace guard (enforced in the service, not the DB): drops runs with
-- pace < 4 mph or > 13 mph (walks misclassified as runs / GPS glitches).
-- Pace is stored after the guard passes so downstream code never sees
-- impossible values.
-- ============================================================================

-- ---------------------------------------------------------------- runs ------

create table runs (
    id                    bigserial primary key,
    user_id               bigint    not null references profiles(id) on delete cascade,
    started_at            timestamp not null,
    ended_at              timestamp not null,
    duration_min          integer   not null check (duration_min between 1 and 1440),
    distance_m            integer   not null check (distance_m >= 0 and distance_m <= 500000),
    -- Pace stored in mph (numeric so we don't lose precision). The 4..13
    -- band is enforced before insert; the CHECK is a belt-and-suspenders
    -- on the DB so a future bug can't slip a 50mph "run" past us.
    pace_mph              numeric(5,2) not null check (pace_mph >= 4.0 and pace_mph <= 13.0),
    calories              integer   check (calories is null or calories >= 0),
    calories_unavailable  boolean   not null default false,
    avg_heart_rate        integer   check (avg_heart_rate is null or avg_heart_rate between 30 and 250),
    max_heart_rate        integer   check (max_heart_rate is null or max_heart_rate between 30 and 250),
    status                text      not null check (status in ('provisional', 'final')),
    captured_at           timestamp not null default now(),
    created_at            timestamp not null default now(),
    check (ended_at > started_at),
    -- Upsert key: the same run posted twice (provisional then final)
    -- collapses to one row. Same user can't have two runs starting at
    -- the same instant.
    unique (user_id, started_at)
);

create index runs_user_started_idx
    on runs (user_id, started_at desc);

-- For the calorie-ingest path: "find all runs that overlap these new
-- buckets so I can re-prorate them."
create index runs_user_ended_idx
    on runs (user_id, ended_at);

create index runs_started_idx
    on runs (started_at desc);

-- ----------------------------------------------------- calorie_buckets ------

create table calorie_buckets (
    id           bigserial primary key,
    user_id      bigint    not null references profiles(id) on delete cascade,
    hour_start   timestamp not null,
    hour_end     timestamp not null,
    -- Apple Health's hourly active-energy buckets. Cap at 1500 kcal/hr
    -- (well above realistic max output for any human) to catch unit
    -- mix-ups (joules vs kcal, etc).
    kcal         integer   not null check (kcal >= 0 and kcal <= 1500),
    captured_at  timestamp not null default now(),
    created_at   timestamp not null default now(),
    check (hour_end > hour_start),
    -- Upsert key: same hourly bucket re-posted updates in place. Apple
    -- Health can revise a bucket's value as more samples arrive within
    -- the hour, so we keep the latest.
    unique (user_id, hour_start)
);

create index calorie_buckets_user_range_idx
    on calorie_buckets (user_id, hour_start, hour_end);

-- For the run-ingest path: "find buckets that overlap this run's
-- window so I can prorate." Ordered by hour_end DESC so the join
-- can short-circuit once we pass the run's started_at.
create index calorie_buckets_user_end_idx
    on calorie_buckets (user_id, hour_end);

-- ----------------------------------------------------------------- RLS ------
-- Match 0006: deny anon/authenticated by default. FastAPI's BYPASSRLS
-- service-role connection reads/writes freely.
alter table public.runs            enable row level security;
alter table public.calorie_buckets enable row level security;
