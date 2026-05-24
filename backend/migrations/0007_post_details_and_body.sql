-- ============================================================================
-- 0007_post_details_and_body.sql
-- ============================================================================
-- Adds two payload columns to `posts` so feed events can carry the
-- data their renderers need, and extends the type CHECK with the two
-- new event types this PR introduces.
--
-- Columns added:
--   details  JSONB  — structured payload, type-specific. Nullable.
--                      Examples:
--                        steps_milestone:  {"threshold": 5000, "date": "2026-05-23"}
--                        leaderboard_recap:{"date": "2026-05-23",
--                                            "top": [{"username": "...", "total": 9567}, ...]}
--   body     TEXT   — pre-rendered display caption. Nullable.
--                      Examples:
--                        steps_milestone:  "hit 5,000 steps"
--                        leaderboard_recap:"Yesterday's top 3"
--
-- New types in the CHECK constraint:
--   steps_milestone   — a user crossed 1k/5k/10k today
--   leaderboard_recap — the 6am daily top-3 recap (system-generated)
--
-- Existing types (sleep, steps, workout) are preserved.
-- ============================================================================

alter table posts add column details jsonb;
alter table posts add column body    text;

alter table posts drop constraint if exists posts_type_check;
alter table posts add constraint posts_type_check
  check (type in (
    'sleep', 'steps', 'workout',
    'steps_milestone',
    'leaderboard_recap'
  ));
