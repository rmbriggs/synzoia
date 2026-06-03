# Join Nav Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an always-visible "Join" entry (→ `/join`) to the app nav — in the desktop header and the mobile bottom nav.

**Architecture:** A `NavLink` in `AppLayout`'s header nav + a `BottomNavItem` in the bottom nav, both pointing at `/join`. No backend/route changes (the `/join` page already exists).

**Tech Stack:** React + react-router-dom + lucide-react; Vitest.

---

## Setup

- [ ] **Step 0:** `cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/join-nav/frontend && [ -e node_modules ] || ln -s /Users/micahbriggs/Developer/synzoia/frontend/node_modules ./node_modules && ls node_modules/.bin/vitest`

---

### Task 1: Join links in the header + bottom nav

**Files:**
- Modify: `frontend/src/components/layout/AppLayout.tsx`
- Test: `frontend/src/__tests__/AppLayout.test.tsx`

- [ ] **Step 1: Write the failing test** — append to `frontend/src/__tests__/AppLayout.test.tsx` (reuses the file's existing `renderLayout` helper):
```tsx
describe('AppLayout Join entry', () => {
  it('shows Join link(s) pointing at /join', () => {
    renderLayout();
    const links = screen.getAllByRole('link', { name: /join/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/join');
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/join-nav/frontend && npm test -- --run src/__tests__/AppLayout.test.tsx`
Expected: FAIL — no link named "Join" exists yet.

- [ ] **Step 3: Implement** in `frontend/src/components/layout/AppLayout.tsx`:

(a) Add `UserPlus` to the lucide import:
```tsx
import { CircleUser, Database, Rss, Trophy, UserPlus, Users } from 'lucide-react';
```

(b) In the desktop header `<nav className="hidden sm:flex …">`, add a Join link after the "Database" `NavLink` (it's the CTA, so always-primary styling rather than the muted `topNavClass`):
```tsx
              <NavLink
                to="/join"
                className="label-mono text-primary hover:text-primary/80 transition-colors"
              >
                Join
              </NavLink>
```

(c) In the mobile bottom nav, add a Join `BottomNavItem` immediately before the "Me" item:
```tsx
          <BottomNavItem
            to="/join"
            icon={<UserPlus size={18} strokeWidth={1.75} />}
            label="Join"
          />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/join-nav/frontend && npm test -- --run src/__tests__/AppLayout.test.tsx`
Expected: PASS (two Join links — header + bottom nav — both `href="/join"`).

- [ ] **Step 5: Full check + commit**

Run: `npm test -- --run && npm run typecheck && npx eslint src/components/layout/AppLayout.tsx`
Expected: all tests pass, typecheck clean, eslint exit 0.

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/join-nav
git add frontend/src/components/layout/AppLayout.tsx frontend/src/__tests__/AppLayout.test.tsx
git commit -m "feat(nav): always-visible Join entry in header + bottom nav

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:** header Join `NavLink` → /join (Step 3b); bottom-nav Join `BottomNavItem` with `UserPlus` icon → /join (Step 3c); always-visible / unconditional (no `currentUser` guard); test asserts both links point at /join (Step 1). ✓
- **Placeholder scan:** none — full code + exact commands.
- **Type consistency:** `UserPlus` imported from lucide-react; `BottomNavItem` props (`to`, `icon`, `label`) match the existing component signature; `NavLink`/`to` consistent with the existing nav links.
