-- ============================================================================
-- 0009_sleep_sessions.sql
-- ============================================================================
-- Extends `sleep` from one-row-per-night to one-row-per-session, so we can
-- represent:
--   - Naps as separate rows on the same date
--   - A night interrupted by a >60-min awakening as two night sessions
--   - Provisional rows (mid-session polls) that get upgraded to final
--   - Review-flagged ambiguous sessions (long naps, very short nights)
--
-- New columns:
--   session_type  — 'night' or 'nap', classified by onset CT time
--                    (20:00-05:00 → night, else nap)
--   status        — 'provisional' (captured while still in progress) or
--                    'final' (wake is >30 min in the past)
--   review_flag   — true when the session falls into the ambiguous band
--                    (nap > 4h or night < 2h)
--   captured_at   — when the row was last touched (insert OR overlap-merge
--                    update); drives provisional/final decisions
--   onset_at      — first non-Awake sample's start. Differs from `bedtime`
--                    in that it skips initial Awake time
--   sleep_date    — CT calendar date for grouping. Replaces `night_of`'s
--                    bedtime-derived semantics with onset-derived. We keep
--                    `night_of` for back-compat with existing read paths.
--
-- Constraints changed:
--   DROP UNIQUE (user_id, night_of)
--     A user can now have multiple sessions per CT date (night + naps).
--     Overlap-dedup at the service layer replaces this constraint.
--
-- Indexes added:
--   sleep (user_id, onset_at, wake_time) — overlap lookups for dedup
--   sleep (user_id, sleep_date)          — per-day aggregations
--
-- Defaults for existing rows:
--   session_type = 'night'  (pre-rewrite rows are all overnight sessions)
--   status       = 'final'  (no pre-rewrite row is provisional)
--   review_flag  = false
--   captured_at  = created_at
--   onset_at     = bedtime  (best approximation without raw samples)
--   sleep_date   = night_of (same semantics, different name going forward)
-- ============================================================================

-- Add new columns with defaults so existing rows are backfilled in-place.
alter table sleep
    add column session_type text   default 'night',
    add column status       text   default 'final',
    add column review_flag  boolean default false,
    add column captured_at  timestamp,
    add column onset_at     timestamp,
    add column sleep_date   date;

-- Backfill from existing values (defaults handle session_type/status/review_flag,
-- but captured_at / onset_at / sleep_date need to derive from sibling columns).
update sleep
   set captured_at = created_at,
       onset_at    = bedtime,
       sleep_date  = night_of
 where captured_at is null;

-- Now that data is in place, tighten NOT NULL + CHECK constraints.
alter table sleep
    alter column session_type set not null,
    alter column status       set not null,
    alter column review_flag  set not null,
    alter column captured_at  set not null,
    alter column onset_at     set not null,
    alter column sleep_date   set not null,
    add  constraint sleep_session_type_check
         check (session_type in ('night', 'nap')),
    add  constraint sleep_status_check
         check (status in ('provisional', 'final'));

-- Drop the old UNIQUE — multiple sessions per (user_id, sleep_date) is
-- now the supported shape. Overlap-dedup happens at the service layer.
alter table sleep drop constraint sleep_user_id_night_of_key;

-- Indexes for the new access patterns.
create index sleep_user_onset_wake_idx
    on sleep (user_id, onset_at, wake_time);

create index sleep_user_sleep_date_idx
    on sleep (user_id, sleep_date);
