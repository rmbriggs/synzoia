-- ============================================================================
-- 0002_sleep_post_extensions.sql
-- ============================================================================
-- Resolves three open questions from 0001's decisions doc §5:
--
--   Q1 (quality_score)      → Personal display only; never a leaderboard
--                              input. Documented via COMMENT ON COLUMN.
--   Q2 (edit / delete)      → Add updated_at + deleted_at (soft delete).
--                              Replace UNIQUE constraint with a partial
--                              unique index that ignores soft-deleted rows
--                              so users can re-post after deletion.
--   Q4 (source)             → Add source column; NOT NULL default 'manual';
--                              CHECK against a known whitelist.
--
-- Q3 (account deletion / hard-delete CASCADE) is deliberately left alone.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Generic touch_updated_at() trigger helper.
-- Reusable for any table that wants automatic updated_at maintenance.
-- ----------------------------------------------------------------------------
create or replace function touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;


-- ----------------------------------------------------------------------------
-- sleep_posts: add updated_at, deleted_at, source
-- ----------------------------------------------------------------------------
alter table sleep_posts
  add column updated_at timestamptz not null default now(),
  add column deleted_at timestamptz,
  add column source     text        not null default 'manual'
                                    check (source in (
                                      'manual',
                                      'apple_health',
                                      'whoop',
                                      'oura',
                                      'fitbit',
                                      'garmin'
                                    ));

-- Bump updated_at on every UPDATE — enforced at the DB so app code can't
-- forget. Applies to edits and to soft-deletes (which UPDATE deleted_at).
create trigger sleep_posts_touch_updated_at
before update on sleep_posts
for each row execute function touch_updated_at();


-- ----------------------------------------------------------------------------
-- Replace UNIQUE (user_id, night_of) with a *partial* unique index that
-- ignores soft-deleted rows.
--
-- Why: the original UNIQUE constraint would block re-posting after a
-- soft-delete, since the deleted row still exists. Filtering on
-- `deleted_at IS NULL` lets the user delete and try again, while still
-- enforcing "one live post per night per user."
-- ----------------------------------------------------------------------------
alter table sleep_posts drop constraint sleep_posts_user_id_night_of_key;

create unique index sleep_posts_user_id_night_of_unique_live
  on sleep_posts (user_id, night_of)
  where deleted_at is null;


-- ----------------------------------------------------------------------------
-- quality_score policy: personal-display-only.
-- Documented via COMMENT so anyone reading the schema sees it; the
-- leaderboard service (when it lands) must read this and skip the column.
-- ----------------------------------------------------------------------------
comment on column sleep_posts.quality_score is
  'Self-reported sleep quality 1-100. PERSONAL DISPLAY ONLY — never use as a leaderboard or ranking input (it is tracker-relative; Whoop 85 != Oura 85). Nullable: user may skip.';


-- ============================================================================
-- end 0002_sleep_post_extensions.sql
-- ============================================================================
