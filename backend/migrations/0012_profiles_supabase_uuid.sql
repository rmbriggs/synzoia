-- ============================================================================
-- 0012_profiles_supabase_uuid.sql
-- ============================================================================
-- Adds the link between Supabase Auth's user UUID and our internal
-- `profiles` row. This is what lets the backend verify a Supabase JWT
-- and resolve it to "which row in our app does this person own."
--
-- Two-track auth design (see auth.py):
--
--   - Web users: sign up + log in via Supabase Auth (email/password).
--     The frontend sends the Supabase-issued JWT on every API call.
--     The backend decodes the JWT, takes the `sub` claim (Supabase
--     user UUID), and looks up the matching profile via this new
--     column.
--
--   - iOS Shortcut: still uses the legacy opaque `profiles.token`
--     string as a machine-to-server API key. Shortcuts can't easily
--     run an OAuth flow, so a static API key is the right shape for
--     that client. The backend tries JWT first; if the token isn't
--     a valid JWT, it falls back to the opaque-token lookup.
--
-- `supabase_user_id` is NULLABLE so the five existing profiles
-- (Max, Angela, Micah, Andy, Sam) continue to work via the legacy
-- token flow until each person separately signs up via Supabase Auth
-- and we link them. Once linked, both auth modes resolve to the same
-- internal row.
--
-- The unique index is partial (only where the column is non-null) so
-- multiple legacy profiles can coexist without colliding on NULL.
-- This is the standard pattern for "optional FK to external system."
-- ============================================================================

alter table public.profiles
    add column if not exists supabase_user_id uuid;

create unique index if not exists profiles_supabase_user_id_unique
    on public.profiles (supabase_user_id)
    where supabase_user_id is not null;
