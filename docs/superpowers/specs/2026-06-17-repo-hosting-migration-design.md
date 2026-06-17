# SP1 — Repo + Hosting Migration Design

**Date:** 2026-06-17
**Status:** Approved (design); implementation plan pending
**Owner:** rmbriggs (Micah)

## Context

This is the first of four sub-projects in a larger effort to (a) shrink the synzoia
team from four people to two and (b) apply the "Santa Cruz coastal" UI design from
`SamM-UATX/synzoia-mockups` to the real React app.

The overall work was decomposed into four sub-projects, each with its own
spec → plan → build cycle:

- **SP1 — Repo + hosting migration (this doc).** New repo, reduced collaborators,
  repointed Vercel, same Supabase, old repo archived.
- **SP2 — Coastal theme foundation.** Map the mockup palette + fonts into the
  existing Tailwind v4 / shadcn token system; restyle shared primitives.
- **SP3 — Page redesigns.** Rebuild Landing, Feed, Profile (and Leaderboard/Users)
  to match the mockups, on top of SP2.
- **SP4 — Messages feature.** Net-new: backend (messages table + endpoints, identity
  via the existing token) and frontend (conversation list + thread). Needs its own
  brainstorm to scope an MVP.

SP1 is sequenced first so that all later redesign work lands in the new repo from
day one.

## Current state (verified 2026-06-17)

- **Repo:** `rmbriggs/synzoia` (public, not a fork). Collaborators besides the owner:
  `astarinmymind`, `maxweinsteinn`, `SamM-UATX` (all push + triage). Owner `rmbriggs`
  is admin.
- **Local clone:** `~/Developer/synzoia`. Its `main` is **behind** `origin/main`
  (local was ~55 commits behind at migration time). The clone is stale, so migration
  must push the authoritative remote history, not this clone.
- **Hosting:** A single Vercel project (monorepo deploy) builds the Vite frontend
  (`frontend/dist`) and runs a Python serverless function `api/index.py` that bundles
  `backend/**`, plus a daily cron `/api/cron/daily-recap` at `0 11 * * *`. Config in
  `vercel.json`.
- **Vercel CLI:** installed (54.3.0), authenticated as `rmbriggs`. No `.vercel/`
  link committed in the repo.
- **Env vars in use:** frontend reads `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`,
  and optional `VITE_API_BASE_URL` (defaults to `/api`). The backend function reads
  its own Supabase/Postgres connection vars. The exact, complete set will be read
  from the live Vercel project during execution (`vercel env ls` / `vercel env pull`).
- **Supabase:** project "Synzoia", ref `yrerlndtavoxbocizjfq`. Unchanged by this
  migration — only the Git repo that Vercel deploys from changes.
- **CI:** `.github/workflows/ci.yml` (ruff + pytest backend; eslint + typecheck +
  vitest + build frontend). Lives in-repo, so it carries over with the history push.

## Goal

A new repository that *is* the canonical `synzoia`: owned by `rmbriggs`, with
`SamM-UATX` as the only other collaborator, deploying from the same Vercel project to
the same Supabase backend (same production domain + env), with the old repo archived
read-only. **The live site stays up throughout.**

## Approach (ordered steps)

1. **Free the name.** Rename `rmbriggs/synzoia` → `rmbriggs/synzoia-archive`. Vercel
   tracks the project by repo ID, so the live deploy keeps working through the rename.
   GitHub adds an automatic redirect from the old name.
2. **Create the new repo + push full history.** Create empty `rmbriggs/synzoia`
   (public). Push the **authoritative** history using a fresh mirror clone of the
   archived repo (`git clone --mirror` of `synzoia-archive`, then `git push --mirror`
   to the new repo) so all branches + tags arrive complete and current — not the
   stale `~/Developer/synzoia` working clone. Issues/PRs/stars/branch-protection do
   not carry; code history + workflows do.
3. **Set collaborators.** Invite `SamM-UATX` (write). New repo starts with no other
   collaborators (astarinmymind + maxweinsteinn are dropped by virtue of the new repo
   starting clean). Re-add branch protection only if desired (note: synzoia's prior
   rule required PR branches be up to date with main).
4. **Carry env + repoint Vercel.** Snapshot the existing project's env vars
   (`vercel env ls`, and pull values as needed), then point the **same** Vercel
   project at the new repo via `vercel git connect <new-repo-url>` (disconnecting the
   archived repo first if required). Keeping the same project preserves the production
   domain, env vars, and Supabase wiring. **Fallback:** if the CLI cannot swap the
   connected repo, the user does it in the dashboard: Project → Settings → Git →
   Disconnect, then Connect the new repo. (May require approving a GitHub→Vercel
   authorization.)
5. **Verify.** Trigger a production deploy from the new repo's `main`. Confirm the
   live URL loads and that reads/writes against Supabase work (feed/leaderboard load,
   a token-authenticated write succeeds). Report the result before proceeding.
6. **Archive the old repo.** Set `synzoia-archive` to archived (read-only). Reversible,
   no data loss. **Pause for explicit user confirmation before this step.**
7. **Re-point local clone.** Set `~/Developer/synzoia` `origin` to the new repo URL,
   fetch, and create a backup tag/branch capturing the pre-migration state.

## Who does what

- **I (Claude) do:** repo rename, new-repo creation, mirror history push, collaborator
  invite, env snapshot, Vercel repoint via CLI, deploy + verification, archiving (after
  confirmation), local-origin repoint.
- **User does / may need to:** approve any GitHub→Vercel authorization prompt; perform
  the 3-click dashboard repoint if the CLI cannot swap the connected repo; SamM-UATX
  must accept the collaborator invite (does not block go-live).

## Non-goals

- No changes to Supabase (schema, data, project) — only the deploying repo changes.
- No UI/redesign work (that is SP2–SP4).
- No migration of GitHub issues/PRs/stars from the old repo.
- No history rewrite, force-push, or deletion. Archiving is reversible.

## Risks & mitigations

- **Vercel CLI may not support swapping the connected repo.** Mitigation: documented
  dashboard fallback; verify the swap by triggering and inspecting a deploy.
- **Stale local clone.** Mitigation: history push uses a fresh mirror clone of the
  remote, not the local working copy.
- **Renaming the live repo mid-flight.** Mitigation: Vercel binds by repo ID and
  GitHub redirects the old name; no pushes occur during the window, so no deploys are
  triggered against the renamed repo.
- **Archiving prematurely.** Mitigation: archive is the last step, only after deploy
  verification, and gated on explicit user confirmation.

## Success criteria

- `rmbriggs/synzoia` exists with full current history, collaborators = `rmbriggs` +
  `SamM-UATX` only.
- The Vercel project deploys from the new repo; production URL is healthy and talks to
  the same Supabase project.
- Old repo is archived (read-only) under a distinct name.
- `~/Developer/synzoia` tracks the new repo, with a backup of the prior state.
