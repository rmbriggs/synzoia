-- ============================================================================
-- 0004_steps.sql
-- ============================================================================
-- Adds the steps table for tracking each user's daily step totals.
--
-- Columns:
--   id         BIGSERIAL  primary key
--   user_id    BIGINT     FK to profiles(id); whose steps these are.
--                          (added by Claude — not in the original 3-column
--                          sketch, but required to make the table useful;
--                          drop if not wanted)
--   timestamp  TIMESTAMP  when this step count was recorded
--   total      INTEGER    total step count at that moment
--
-- Notes:
--   - On delete of a profile, that user's step rows go with them (CASCADE).
--   - No CHECK on total bounds yet — Apple Health caps at ~6-digit daily
--     counts; we can add a sanity bound later if needed.
-- ============================================================================

create table steps (
    id         bigserial primary key,
    user_id    bigint    not null references profiles(id) on delete cascade,
    timestamp  timestamp not null,
    total      integer   not null check (total >= 0)
);
