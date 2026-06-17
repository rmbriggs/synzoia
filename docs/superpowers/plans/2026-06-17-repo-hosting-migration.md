# SP1 — Repo + Hosting Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move synzoia onto a new repo (`rmbriggs/synzoia`) with only Micah + SamM-UATX as collaborators, deploying from the same Vercel project to the same Supabase backend, with the old repo archived read-only — keeping the live site up throughout.

**Architecture:** Rename the existing repo to free the `synzoia` name; create a fresh `synzoia` and populate it from a mirror clone of the authoritative remote history; reconnect the *same* Vercel project (so env vars + domain + Supabase wiring are preserved) to the new repo; verify a production deploy; archive the old repo last, after explicit confirmation.

**Tech Stack:** `gh` CLI (GitHub), `git` (mirror clone/push), `vercel` CLI (54.3.0), Supabase (unchanged).

## Global Constraints

- **Keep the SAME Vercel project** — only swap its connected Git repo. Never delete/recreate the project (that would drop env vars + the production domain). [verbatim from spec: "point the same Vercel project at the new repo … preserves the production domain, env vars, and Supabase wiring"]
- **No history rewrite, force-push, or deletion.** Archiving is reversible; it is the only "destructive-ish" action and is gated on explicit user confirmation.
- **Push the authoritative remote history** via a fresh `git clone --mirror` of the remote — NOT the stale `~/Developer/synzoia` working clone.
- **New repo is public** (matches current visibility).
- **Supabase is untouched** — project ref `yrerlndtavoxbocizjfq` stays; only the deploying repo changes.
- **Collaborators on the new repo:** `rmbriggs` (owner) + `SamM-UATX` only. `astarinmymind` and `maxweinsteinn` are not added.
- Commit messages end with the `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.

**Runtime-discovered values** (captured by Task 1, reused later — referenced as shell vars):
- `VERCEL_PROJECT` — the Vercel project name for synzoia.
- `PROD_URL` — the production URL of that project.
- `BACKUP_DIR` — `~/Developer/synzoia-mirror-backup.git` (mirror backup, outside any repo).

---

### Task 1: Pre-flight — capture state & create safety backups

**Files:**
- Create: `~/Developer/synzoia-mirror-backup.git` (mirror clone — backup, not committed)
- Create: `~/synzoia-migration-snapshot.txt` (recorded state — backup, not committed)
- Create: `~/synzoia-env-backup.local` (env values pulled from Vercel — backup, NEVER committed)

**Outputs (consumed by later tasks):** `VERCEL_PROJECT`, `PROD_URL`, `BACKUP_DIR`, the list of env var names.

- [ ] **Step 1: Record current GitHub state**

```bash
{
  echo "=== captured $(date) ==="
  echo "--- repo ---"
  gh repo view rmbriggs/synzoia --json name,visibility,defaultBranchRef,isFork
  echo "--- collaborators ---"
  gh api repos/rmbriggs/synzoia/collaborators --jq '.[] | "\(.login) \(.permissions)"'
  echo "--- branch protection (main) ---"
  gh api repos/rmbriggs/synzoia/branches/main/protection 2>&1 | head -40
} | tee ~/synzoia-migration-snapshot.txt
```

Expected: a snapshot file listing the repo, 3 collaborators + owner, and the current `main` protection rule (or a 404 if none).

- [ ] **Step 2: Create a mirror backup of the authoritative remote**

```bash
rm -rf ~/Developer/synzoia-mirror-backup.git
git clone --mirror https://github.com/rmbriggs/synzoia.git ~/Developer/synzoia-mirror-backup.git
git -C ~/Developer/synzoia-mirror-backup.git for-each-ref --format='%(refname)' | grep -E 'refs/(heads|tags)/' | sed 's#refs/heads/##' | head
```

Run + Expected: clone succeeds; the ref list shows `main` plus the other branches/tags. This is the full-history source for Task 3 AND the rollback safety net.

- [ ] **Step 3: Identify the Vercel project**

```bash
vercel project ls 2>&1 | head -30
```

Expected: a table of projects; note the synzoia project's exact name → set `VERCEL_PROJECT` to it. (Likely `synzoia`.)

- [ ] **Step 4: Link the directory + back up env vars and prod URL**

```bash
cd ~/Developer/synzoia
vercel link --yes --project "$VERCEL_PROJECT"      # non-interactive link to existing project
vercel env ls > ~/synzoia-env-names.txt            # names + targets only (safe to keep)
vercel env pull ~/synzoia-env-backup.local --yes   # actual VALUES — backup only, do NOT commit
vercel ls "$VERCEL_PROJECT" 2>&1 | head -15        # find the production URL
```

Expected: `.vercel/project.json` is created (gitignored already), `~/synzoia-env-names.txt` lists `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and the backend Supabase/Postgres vars; `vercel ls` shows the latest production deployment URL → set `PROD_URL` to it (e.g. `https://synzoia.vercel.app` or the custom domain from `vercel domains ls`).

- [ ] **Step 5: Sanity-check the live site BEFORE any change (baseline)**

```bash
curl -s -o /dev/null -w "%{http_code}\n" "$PROD_URL"
curl -s "$PROD_URL/api/leaderboard" | head -c 300; echo
```

Expected: `200`, and the API returns JSON (proves the baseline Supabase-backed read works). Record this as the "known good" baseline to compare against after the repoint.

---

### Task 2: Rename old repo to free the `synzoia` name

**Files:** none (GitHub operation).

**Inputs:** baseline from Task 1. **Outputs:** old repo now at `rmbriggs/synzoia-archive`.

- [ ] **Step 1: Rename the repo**

```bash
gh repo rename synzoia-archive --repo rmbriggs/synzoia --yes
```

Expected: confirmation that the repo is now `rmbriggs/synzoia-archive`.

- [ ] **Step 2: Verify the rename + redirect, and that Vercel is unaffected**

```bash
gh repo view rmbriggs/synzoia-archive --json name,visibility | head
gh repo view rmbriggs/synzoia --json name 2>&1 | head -3   # redirect: resolves to synzoia-archive
curl -s -o /dev/null -w "%{http_code}\n" "$PROD_URL"        # site still up (Vercel binds by repo ID)
```

Expected: `synzoia-archive` exists; the old path redirects; `PROD_URL` still returns `200`. No deploy was triggered (no pushes occurred).

---

### Task 3: Create the new repo + push full history

**Files:** none (GitHub + git operation).

**Inputs:** `BACKUP_DIR` mirror from Task 1. **Outputs:** `rmbriggs/synzoia` populated with full history, default branch `main`.

- [ ] **Step 1: Create the empty new repo**

```bash
gh repo create rmbriggs/synzoia --public --description "synzoia — steps + sleep tracker"
```

Expected: confirmation the empty repo `rmbriggs/synzoia` was created (no README/auto-init).

- [ ] **Step 2: Push the full mirror history into it**

```bash
git -C ~/Developer/synzoia-mirror-backup.git push --mirror https://github.com/rmbriggs/synzoia.git
```

Expected: all `refs/heads/*` and `refs/tags/*` push successfully.

- [ ] **Step 3: Set the default branch + verify contents**

```bash
gh repo edit rmbriggs/synzoia --default-branch main
echo "--- branch/tag count (new) ---"; gh api repos/rmbriggs/synzoia/branches --jq 'length'
echo "--- latest commit (new) ---";   gh api repos/rmbriggs/synzoia/commits/main --jq '.sha[0:7] + " " + .commit.message' | head -1
echo "--- CI workflow present? ---";   gh api repos/rmbriggs/synzoia/contents/.github/workflows/ci.yml --jq '.name'
```

Expected: default branch is `main`; latest commit on new `main` matches `origin/main` of the old repo (`f9ce623` at capture time, or newer if collaborators pushed since); `ci.yml` is present.

---

### Task 4: Set collaborators + branch protection on the new repo

**Files:** none (GitHub operation).

**Inputs:** new repo from Task 3. **Outputs:** collaborators = owner + SamM-UATX; main protected to require CI + up-to-date branches.

- [ ] **Step 1: Invite SamM-UATX (write access)**

```bash
gh api -X PUT repos/rmbriggs/synzoia/collaborators/SamM-UATX -f permission=push
```

Expected: `201` (invitation created) or `204` (already a collaborator).

- [ ] **Step 2: Verify the collaborator set**

```bash
gh api repos/rmbriggs/synzoia/collaborators --jq '.[].login'
gh api repos/rmbriggs/synzoia/invitations --jq '.[].invitee.login'
```

Expected: collaborators = `rmbriggs` (+ `SamM-UATX` once accepted); a pending invitation for `SamM-UATX`; NO `astarinmymind` / `maxweinsteinn`.

- [ ] **Step 3: Re-add branch protection on main (match prior workflow)**

```bash
gh api -X PUT repos/rmbriggs/synzoia/branches/main/protection \
  --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["backend", "frontend"] },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON
```

Expected: `200` with the protection object. `strict: true` enforces "branch up to date with main" before merge; `contexts` requires the CI jobs to pass. (If the CI job names differ from `backend`/`frontend`, read them from a first PR's checks and adjust — see Task 6.)

---

### Task 5: Repoint the Vercel project to the new repo

**Files:** none (Vercel operation).

**Inputs:** `VERCEL_PROJECT` (linked in Task 1), env vars already on the project. **Outputs:** the same Vercel project now deploys from `rmbriggs/synzoia`.

- [ ] **Step 1: Disconnect the old repo, connect the new one (CLI)**

```bash
cd ~/Developer/synzoia
vercel git disconnect --yes 2>&1 | head -10
vercel git connect https://github.com/rmbriggs/synzoia 2>&1 | head -20
```

Expected: confirmation the project is now connected to `rmbriggs/synzoia`.

**Fallback (if the CLI errors or won't swap the repo):** hand the user this exact path — Vercel dashboard → the synzoia project → **Settings → Git → Disconnect**, then **Connect Git Repository → rmbriggs/synzoia**. They may need to approve a GitHub→Vercel authorization. Do NOT create a new project.

- [ ] **Step 2: Confirm env vars survived + the connection**

```bash
vercel env ls 2>&1 | head -20                      # same names as ~/synzoia-env-names.txt
diff <(vercel env ls | awk '{print $1}' | sort) <(awk '{print $1}' ~/synzoia-env-names.txt | sort) && echo "ENV NAMES MATCH"
```

Expected: env var names are unchanged (project kept its env). If they match, the Supabase wiring is intact.

---

### Task 6: Trigger a production deploy + verify live site & Supabase

**Files:**
- Push: `worktree-sp1-infra-migration` branch (the SP1 spec + plan) to the new repo
- This doubles as the deploy trigger and a CI smoke test.

**Inputs:** new repo connected to Vercel (Task 5), `PROD_URL`. **Outputs:** a green production deploy from the new repo; spec/plan landed on new `main`.

- [ ] **Step 1: Push the spec/plan branch to the new repo + open a PR**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/sp1-infra-migration
git remote set-url origin https://github.com/rmbriggs/synzoia.git   # this worktree now points at the new repo
git push -u origin worktree-sp1-infra-migration
gh pr create --repo rmbriggs/synzoia --base main --head worktree-sp1-infra-migration \
  --title "docs: SP1 repo + hosting migration spec & plan" \
  --body "Migration design + implementation plan (SP1). Merging exercises CI + the new Vercel Git deploy pipeline."
```

Expected: branch pushes; a PR is created.

- [ ] **Step 2: Watch CI; reconcile protection contexts if needed**

```bash
gh pr checks --repo rmbriggs/synzoia worktree-sp1-infra-migration --watch
```

Expected: CI runs (`backend` + `frontend` jobs) and passes. If the actual check names differ from the `contexts` set in Task 4 Step 3, re-run that PUT with the real names, then re-check.

- [ ] **Step 3: Merge the PR (triggers the production deploy)**

```bash
gh pr merge --repo rmbriggs/synzoia worktree-sp1-infra-migration --merge
```

Expected: merge succeeds (branch was up to date + checks green). Vercel's Git integration starts a production deploy from new `main`.

- [ ] **Step 4: Verify the deploy came from the new repo**

```bash
vercel ls "$VERCEL_PROJECT" 2>&1 | head -8        # newest deployment should be "Production" and recent
vercel inspect "$PROD_URL" 2>&1 | grep -iE 'repo|git|commit' | head
```

Expected: a fresh Production deployment whose Git source is `rmbriggs/synzoia`.

- [ ] **Step 5: Verify the live site + Supabase reads (compare to Task 1 baseline)**

```bash
curl -s -o /dev/null -w "%{http_code}\n" "$PROD_URL"
curl -s "$PROD_URL/api/leaderboard" | head -c 300; echo
curl -s -o /dev/null -w "%{http_code}\n" "$PROD_URL/api/cron/daily-recap"   # cron route resolves
```

Expected: `200` on the site; `/api/leaderboard` returns the same shape of JSON as the Task 1 baseline (proves Supabase reads work from the new deploy). The cron route resolves (the cron itself is defined in `vercel.json` and registers automatically).

---

### Task 7: Confirm, then archive the old repo

**Files:** none (GitHub operation).

**Inputs:** verified deploy from Task 6. **Outputs:** `rmbriggs/synzoia-archive` archived (read-only).

- [ ] **Step 1: HARD PAUSE — confirm with the user**

Report: "New repo is live, Vercel deploys from it, Supabase reads verified. Ready to archive `rmbriggs/synzoia-archive` (read-only, reversible). Confirm?" Wait for an explicit yes. Do not proceed without it.

- [ ] **Step 2: Archive the old repo**

```bash
gh repo archive rmbriggs/synzoia-archive --yes
```

Expected: confirmation the repo is archived.

- [ ] **Step 3: Verify**

```bash
gh repo view rmbriggs/synzoia-archive --json isArchived --jq '.isArchived'
```

Expected: `true`.

---

### Task 8: Re-point the local clone + record outcome

**Files:**
- Modify: `~/Developer/synzoia` git remote (`origin` → new repo)
- Create: a backup tag capturing the pre-migration HEAD

**Inputs:** archived old repo, live new repo. **Outputs:** local clone tracks the new repo; pre-migration state tagged.

- [ ] **Step 1: Tag the pre-migration state from the mirror backup, push it to the new repo**

```bash
git -C ~/Developer/synzoia-mirror-backup.git tag pre-migration-2026-06-17 main 2>/dev/null || true
git -C ~/Developer/synzoia-mirror-backup.git push https://github.com/rmbriggs/synzoia.git pre-migration-2026-06-17
```

Expected: a `pre-migration-2026-06-17` tag exists on the new repo pointing at the migrated HEAD.

- [ ] **Step 2: Re-point the local working clone's origin**

```bash
cd ~/Developer/synzoia
git remote set-url origin https://github.com/rmbriggs/synzoia.git
git fetch origin --prune
git remote -v
```

Expected: `origin` is `https://github.com/rmbriggs/synzoia.git`; fetch succeeds.

- [ ] **Step 3: Final summary**

Report the end state: new repo URL, collaborators, Vercel project + production URL confirmed healthy, old repo archived, local clone re-pointed, and the locations of the backups (`~/Developer/synzoia-mirror-backup.git`, `~/synzoia-env-backup.local`).

---

## Self-Review

**Spec coverage:**
- New repo, full history → Tasks 2–3. ✓
- Collaborators = owner + SamM-UATX only → Task 4. ✓
- Reuse Supabase, repoint Vercel (same project, preserve env/domain) → Tasks 1, 5. ✓
- Live site stays up → baseline (T1), checks after rename (T2) and after repoint (T6). ✓
- Archive old repo, confirmation-gated, last → Task 7. ✓
- Re-point local clone + backup → Tasks 1, 8. ✓
- No history rewrite/force-push; archive reversible → global constraints; honored throughout. ✓

**Placeholder scan:** Runtime-discovered values (`VERCEL_PROJECT`, `PROD_URL`) are captured by explicit commands in Task 1 and referenced as shell vars — not placeholders. No TBD/TODO left.

**Type/name consistency:** `BACKUP_DIR`/mirror path consistent across Tasks 1, 3, 8. Branch name `worktree-sp1-infra-migration` consistent (Task 6). CI context names (`backend`/`frontend`) flagged as verify-and-adjust in Task 6 Step 2 to stay consistent with Task 4 Step 3.

## Notes / Open Risks

- **Vercel CLI repo swap** (Task 5) is the least certain step; the dashboard fallback is documented inline.
- **CI check names** for branch protection (Task 4) are an assumption (`backend`, `frontend`); Task 6 reconciles them against the first real PR run.
- **SamM-UATX** must accept the invite to gain access; this does not block any step.
