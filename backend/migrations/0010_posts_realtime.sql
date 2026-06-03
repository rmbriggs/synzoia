-- ============================================================================
-- 0010_posts_realtime.sql
-- ============================================================================
-- Codifies the Supabase Realtime setup for the activity feed. Previously
-- this lived only in the Supabase dashboard (applied via the SQL Editor
-- by hand), which meant a fresh deploy / re-created Supabase project
-- would silently produce a feed that fetched once and never updated —
-- the broadcast plumbing simply wasn't there.
--
-- Two things this migration sets up:
--
--   1. RLS SELECT policy on `posts` for the `anon` and `authenticated`
--      roles. Supabase Realtime evaluates RLS using the role of the
--      JWT presented over the WebSocket. With RLS enabled (see 0006)
--      and no SELECT policy, the service silently drops every event
--      before it reaches the client. The policy below makes the feed
--      world-readable — appropriate for a public group activity feed.
--      The service-role connection FastAPI uses for writes is BYPASSRLS,
--      so this policy only affects what Realtime + the frontend's anon
--      client can see.
--
--   2. Adds `public.posts` to the `supabase_realtime` publication. The
--      Realtime service only forwards changes for tables that are
--      explicitly part of that publication; without this line, a row
--      inserted into `posts` produces zero broadcast events even with
--      the right RLS policies in place.
--
-- Both operations are wrapped in DO blocks so re-running this migration
-- is a no-op. The check against `pg_policy` matches on policy name +
-- table OID; the check against `pg_publication_tables` matches the
-- (pubname, tablename) tuple. If either is already present, the body
-- is skipped — important because the live database already has these
-- objects (they were applied by hand during initial setup).
-- ============================================================================

-- ---------------------------------------------------------------- policy ----

do $$
begin
  if not exists (
    select 1
      from pg_policy
     where polname = 'anon can read posts'
       and polrelid = 'public.posts'::regclass
  ) then
    create policy "anon can read posts"
      on public.posts
      for select
      to anon, authenticated
      using (true);
  end if;
end
$$;

-- ----------------------------------------------------------- publication ----

do $$
begin
  if not exists (
    select 1
      from pg_publication_tables
     where pubname = 'supabase_realtime'
       and schemaname = 'public'
       and tablename = 'posts'
  ) then
    alter publication supabase_realtime add table public.posts;
  end if;
end
$$;
