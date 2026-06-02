# Feed as Default View (Hide Landing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Feed the default view — `/` redirects to `/feed` — and unroute the Landing page (keeping `Landing.tsx` on disk).

**Architecture:** A single change in `frontend/src/App.tsx`: swap the index route from `<Landing />` to `<Navigate to="/feed" replace />` and drop the now-unused `Landing` import. One smoke test is flipped from asserting Landing-at-`/` to Feed-at-`/`.

**Tech Stack:** React + react-router-dom v6 (`Navigate`), Vitest + React Testing Library.

---

## Setup (worktree only)

The isolated worktree has no `node_modules`. This change adds **no new dependencies**, so symlink the main checkout's modules instead of a full install:

- [ ] **Step 0: Make deps reachable**

Run:
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default/frontend
ln -s /Users/micahbriggs/Developer/synzoia/frontend/node_modules ./node_modules
```
Expected: `node_modules/.bin/vitest` resolves.

---

### Task 1: Redirect `/` to `/feed` and unroute Landing

**Files:**
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/__tests__/smoke.test.tsx:38-43` (flip the existing landing test)

- [ ] **Step 1: Flip the failing test**

In `frontend/src/__tests__/smoke.test.tsx`, replace the existing test (currently lines 38-43):

```tsx
  it('renders the landing page at "/" when logged out', () => {
    const { container } = renderAt('/');
    // The "More than a step counter." headline is unique to the
    // landing page.
    expect(container.textContent).toContain('More than a step counter.');
  });
```

with:

```tsx
  it('renders the Feed at "/" (the default view)', () => {
    const { container } = renderAt('/');
    // "/" now redirects to /feed. The Feed's description is unique to it;
    // the Landing headline must no longer appear at the default route.
    expect(container.textContent).toContain('Recent milestones and recaps.');
    expect(container.textContent).not.toContain('More than a step counter.');
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
npm test -- --run src/__tests__/smoke.test.tsx
```
Expected: FAIL — the new test errors because `/` still renders Landing (contains "More than a step counter.", not "Recent milestones and recaps.").

- [ ] **Step 3: Change the router**

In `frontend/src/App.tsx`:

(a) Update the react-router-dom import to add `Navigate`:
```tsx
import { Navigate, Route, Routes } from 'react-router-dom';
```

(b) Delete the Landing import line:
```tsx
import Landing from '@/pages/Landing';
```

(c) Replace the index route:
```tsx
      <Route path="/" element={<Landing />} />
```
with:
```tsx
      <Route path="/" element={<Navigate to="/feed" replace />} />
```

Resulting file:
```tsx
import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import Join from '@/pages/Join';
import StyleGuide from '@/pages/StyleGuide';
import DbExplorer from '@/pages/DbExplorer';
import Feed from '@/pages/Feed';
import Leaderboard from '@/pages/Leaderboard';
import Profile from '@/pages/Profile';
import Users from '@/pages/Users';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/feed" replace />} />
      <Route path="/join" element={<Join />} />
      <Route path="/style-guide" element={<StyleGuide />} />
      <Route element={<AppLayout />}>
        <Route path="/feed" element={<Feed />} />
        <Route path="/users" element={<Users />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/u/:username" element={<Profile />} />
        <Route path="/db" element={<DbExplorer />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
npm test -- --run src/__tests__/smoke.test.tsx
```
Expected: PASS — `/` redirects to `/feed`, the Feed renders ("Recent milestones and recaps." present, "More than a step counter." absent), and the route-loop `<h1>`-at-`/` assertion still passes (Feed's `PageHeader title="Feed"` renders an `<h1>`).

- [ ] **Step 5: Run the full check (suite + typecheck + lint)**

Run:
```bash
npm test -- --run && npm run typecheck && npx eslint src/App.tsx src/__tests__/smoke.test.tsx
```
Expected: all tests pass, typecheck clean, eslint exits 0 for the two changed files. (Pre-existing repo-wide lint errors in unrelated files — `ConnectionStatus.tsx` etc. — are out of scope.)

- [ ] **Step 6: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default
git add frontend/src/App.tsx frontend/src/__tests__/smoke.test.tsx
git commit -m "feat(routing): make Feed the default view; unroute Landing

/ now redirects to /feed (replace, so back-button stays clean). Landing
is removed from the router but Landing.tsx is kept on disk for easy
un-hiding later. Flips the smoke test that asserted Landing-at-/ to
assert Feed-at-/.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:** `/`→`/feed` redirect with `replace` (Task 1 Step 3c); drop Landing import + route (Step 3a/b); Landing.tsx untouched on disk (no task deletes it); smoke test flipped (Steps 1-4). All spec sections covered.
- **Placeholder scan:** none — every step has exact code/commands.
- **Type consistency:** `Navigate` imported from `react-router-dom`; `to="/feed"` matches the existing `/feed` route; test assertions use real copy strings ("Recent milestones and recaps." from `Feed.tsx`, "More than a step counter." from `Landing.tsx`).
