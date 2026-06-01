-- ============================================================================
-- 0010_workouts.sql
-- ============================================================================
-- Adds the `workouts` table to support two POST endpoints:
--   POST /api/workouts/run       — distance-based (runs, rides, walks)
--   POST /api/workouts/calories  — calorie-burn-based (lifting, yoga,
--                                                       HIIT, etc.)
--
-- Both endpoints take a workout window (started_at + ended_at) plus
-- per-kind metrics. Smart matching: incoming workouts that overlap an
-- existing row (within 30 min) for the same user merge into it rather
-- than creating a duplicate — matches the sleep-sessionization pattern
-- and absorbs the iOS Shortcut's repeated polling.
--
-- Columns:
--   id              BIGSERIAL  primary key
--   user_id         BIGINT     FK profiles(id), CASCADE
--   workout_kind    TEXT       'run' | 'calories'. CHECK-constrained;
--                              determines which metric columns are
--                              meaningful for this row.
--   started_at      TIMESTAMP  workout window start (UTC, naive)
--   ended_at        TIMESTAMP  workout window end. CHECK > started_at.
--   duration_min    INTEGER    derived = ended_at − started_at minutes;
--                              stored for fast aggregations
--   distance_m      INTEGER    nullable; populated for 'run' kind
--   active_calories INTEGER    nullable; populated for both kinds
--                              ('run' may include calories, 'calories'
--                              kind always sets this)
--   avg_heart_rate  INTEGER    nullable; bpm
--   max_heart_rate  INTEGER    nullable; bpm
--   captured_at     TIMESTAMP  when the row was last touched (insert
--                              OR overlap-merge update). Provisional/
--                              final logic could use this in the
--                              future; v1 just exposes the field.
--   created_at      TIMESTAMP  insert time
--
-- Indexes:
--   workouts (user_id, started_at, ended_at) — overlap dedup
--   workouts (user_id, started_at DESC)      — per-user history
--   workouts (started_at DESC)               — global feed
--
-- RLS: enabled to match 0006 — FastAPI's BYPASSRLS-capable role still
-- reads/writes freely.
-- ============================================================================

create table workouts (
    id              bigserial primary key,
    user_id         bigint    not null references profiles(id) on delete cascade,
    workout_kind    text      not null check (workout_kind in ('run', 'calories')),
    started_at      timestamp not null,
    ended_at        timestamp not null,
    duration_min    integer   not null check (duration_min between 1 and 1440),
    distance_m      integer            check (distance_m       is null or distance_m       >= 0),
    active_calories integer            check (active_calories  is null or active_calories  >= 0),
    avg_heart_rate  integer            check (avg_heart_rate   is null or avg_heart_rate   between 30 and 250),
    max_heart_rate  integer            check (max_heart_rate   is null or max_heart_rate   between 30 and 250),
    captured_at     timestamp not null default now(),
    created_at      timestamp not null default now(),
    check (ended_at > started_at)
);

create index workouts_user_overlap_idx
    on workouts (user_id, started_at, ended_at);

create index workouts_user_started_idx
    on workouts (user_id, started_at desc);

create index workouts_started_idx
    on workouts (started_at desc);

-- Match 0006: deny anon/authenticated roles by default.
alter table public.workouts enable row level security;
