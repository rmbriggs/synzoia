-- ============================================================================
-- 0012_lowercase_usernames.sql
-- ============================================================================
-- Normalize all usernames to lowercase.
--
-- Usernames are now lowercase everywhere: sign-up coerces new names to
-- lowercase (routes/profiles.py) and per-user lookups compare
-- case-insensitively (services/{sleep,steps,posts}.py). This migration
-- back-fills the existing rows so stored data matches that invariant.
--
-- Two columns hold a username:
--   1. profiles.username  — the canonical identity
--   2. posts.username     — denormalized onto each post for the feed
--                           (matches the existing schema; there is no
--                           rename feature, so it can't drift)
--
-- Both UPDATEs are guarded by `WHERE username <> lower(username)`, so the
-- migration is idempotent — re-running it against an already-normalized
-- DB touches zero rows and returns "Success. No rows returned."
--
-- Collision note: lowercasing cannot create a duplicate here because no
-- two current usernames differ only by case. If that ever changes, the
-- UNIQUE constraint on profiles.username will reject the UPDATE, which is
-- the correct, loud failure — resolve the clash by hand before retrying.
--
-- Recap posts embed a `details.top[].username` list. Those are left as-is:
-- every existing recap already holds lowercase names, future recaps derive
-- from the now-normalized profiles, and recap mention-matching compares
-- case-insensitively, so no JSONB rewrite is needed.
-- ============================================================================

UPDATE profiles SET username = lower(username) WHERE username <> lower(username);

UPDATE posts SET username = lower(username) WHERE username <> lower(username);
