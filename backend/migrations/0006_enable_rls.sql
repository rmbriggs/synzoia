-- ============================================================================
-- 0006_enable_rls.sql
-- ============================================================================
-- Enables Row Level Security on the three v1 tables. Resolves the
-- Supabase advisor warning that flagged them as fully exposed to the
-- `anon` and `authenticated` roles used by supabase-js client libraries.
--
-- Why this is safe for the backend:
--   FastAPI connects via the pgbouncer transaction pooler as the
--   `postgres` role. That role has the BYPASSRLS attribute by default
--   in Supabase, so server-side queries continue to work with no
--   policies declared. Verify this by hitting /api/health/db after
--   applying — it should still report ok: true.
--
-- Why this is safe for the frontend:
--   The current frontend doesn't use supabase-js. All browser-facing
--   reads/writes go through the FastAPI backend. The anon-key surface
--   has nothing pointed at it today; this migration just hardens what
--   would otherwise be silently open if someone added a direct
--   supabase-js call.
--
-- What is NOT done here (deliberately):
--   No POLICY statements. With no policies, anon/authenticated roles
--   are denied access to all rows — that's the goal. When/if Realtime
--   subscriptions land (per CLAUDE.md's plan), policies will need to
--   be added so the realtime listener role can read the relevant
--   tables.
-- ============================================================================

alter table public.profiles enable row level security;
alter table public.steps    enable row level security;
alter table public.posts    enable row level security;
