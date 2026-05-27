# Client-side current-user + quick profile access — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a visitor mark a profile as "me" (stored only in `localStorage`), and give them a profile icon in the header + mobile nav that jumps straight to their own profile.

**Architecture:** A `useCurrentUser` hook owns a `localStorage`-backed username and broadcasts changes via a `window` CustomEvent so every hook instance (Profile button + persistent header icon) stays in sync without a remount. The Profile page gets a "Make this me" / disabled "✓ This is you" button; `AppLayout` gets a `CircleUser` link (header + mobile pill) pointing at `/u/<currentUser>` or `/users` when unset. No backend changes.

**Tech Stack:** React + TypeScript + Vite, React Query (unrelated here), Tailwind, lucide-react, vitest + @testing-library/react (v16, `renderHook` available).

**Spec:** `docs/superpowers/specs/2026-05-26-current-user-design.md`

**Branch:** `worktree-users-pages` (already open as PR #38; these commits extend that PR since the button depends on the Profile page introduced there).

---

## File Structure

### Commit 1 — hook + button (`feat(frontend): useCurrentUser hook + "make this me" button`)

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/hooks/useCurrentUser.ts` | create | localStorage-backed current-user state + CustomEvent sync |
| `frontend/src/hooks/__tests__/useCurrentUser.test.ts` | create | Hook unit tests |
| `frontend/src/pages/Profile.tsx` | modify | "Make this me" / "✓ This is you" button below the header |
| `frontend/src/__tests__/Profile.test.tsx` | modify | Button state + click tests |

### Commit 2 — profile icon (`feat(frontend): profile icon in header + mobile nav`)

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/components/layout/AppLayout.tsx` | modify | `CircleUser` link in header top-right + "Me" item in mobile pill |
| `frontend/src/__tests__/AppLayout.test.tsx` | create | Icon/pill destination tests |

---

## How to run tests

From the worktree root:

```bash
cd frontend && npm test -- --run        # full vitest suite
cd frontend && npm test -- --run useCurrentUser   # one file
cd frontend && npx tsc --noEmit          # type check
```

Baseline before this plan: 53 tests across 10 files, all green.

---

# Commit 1 — hook + button

## Task 1: `useCurrentUser` hook

**Files:**
- Create: `frontend/src/hooks/useCurrentUser.ts`
- Test: `frontend/src/hooks/__tests__/useCurrentUser.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/__tests__/useCurrentUser.test.ts`:

```ts
import { afterEach, describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useCurrentUser } from '@/hooks/useCurrentUser';

const KEY = 'synzoia.currentUser';

afterEach(() => {
  window.localStorage.clear();
});

describe('useCurrentUser', () => {
  it('returns null when nothing is stored', () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.currentUser).toBeNull();
  });

  it('reads an existing stored value on mount', () => {
    window.localStorage.setItem(KEY, 'alice');
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current.currentUser).toBe('alice');
  });

  it('setCurrentUser persists and updates the value', () => {
    const { result } = renderHook(() => useCurrentUser());
    act(() => result.current.setCurrentUser('bob'));
    expect(result.current.currentUser).toBe('bob');
    expect(window.localStorage.getItem(KEY)).toBe('bob');
  });

  it('clearCurrentUser resets to null and removes the key', () => {
    window.localStorage.setItem(KEY, 'alice');
    const { result } = renderHook(() => useCurrentUser());
    act(() => result.current.clearCurrentUser());
    expect(result.current.currentUser).toBeNull();
    expect(window.localStorage.getItem(KEY)).toBeNull();
  });

  it('syncs a second hook instance via the custom event', () => {
    const a = renderHook(() => useCurrentUser());
    const b = renderHook(() => useCurrentUser());
    act(() => a.result.current.setCurrentUser('carol'));
    // The second instance hears the synzoia:currentuser event and updates.
    expect(b.result.current.currentUser).toBe('carol');
  });
});
```

- [ ] **Step 2: Run the test, expect failure**

Run: `cd frontend && npm test -- --run useCurrentUser`
Expected: FAIL — `Cannot find module '@/hooks/useCurrentUser'` (file doesn't exist yet).

- [ ] **Step 3: Implement the hook**

Create `frontend/src/hooks/useCurrentUser.ts`:

```ts
import { useEffect, useState } from 'react';

const STORAGE_KEY = 'synzoia.currentUser';
const SYNC_EVENT = 'synzoia:currentuser';

function readStored(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const v = window.localStorage?.getItem?.(STORAGE_KEY);
    return v && v.length > 0 ? v : null;
  } catch {
    return null;
  }
}

function writeStored(username: string) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage?.setItem?.(STORAGE_KEY, username);
  } catch {
    /* swallow — feature-detect, don't throw */
  }
}

function clearStored() {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage?.removeItem?.(STORAGE_KEY);
  } catch {
    /* swallow */
  }
}

/**
 * Client-side "current user" pointer, persisted to localStorage.
 *
 * Purely a browser convenience — there's no auth. Multiple hook
 * instances stay in sync within a tab via a custom window event
 * (dispatched on every write) and across tabs via the native
 * `storage` event. Mirrors the localStorage discipline in useTheme.
 */
export function useCurrentUser() {
  const [currentUser, setState] = useState<string | null>(() => readStored());

  useEffect(() => {
    function resync() {
      setState(readStored());
    }
    window.addEventListener(SYNC_EVENT, resync);
    window.addEventListener('storage', resync);
    return () => {
      window.removeEventListener(SYNC_EVENT, resync);
      window.removeEventListener('storage', resync);
    };
  }, []);

  function setCurrentUser(username: string) {
    writeStored(username);
    setState(username);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(SYNC_EVENT));
    }
  }

  function clearCurrentUser() {
    clearStored();
    setState(null);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(SYNC_EVENT));
    }
  }

  return { currentUser, setCurrentUser, clearCurrentUser };
}

export default useCurrentUser;
```

- [ ] **Step 4: Run the test, expect pass**

Run: `cd frontend && npm test -- --run useCurrentUser`
Expected: 5 passed.

- [ ] **Step 5: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no output (clean).

## Task 2: "Make this me" button on Profile

**Files:**
- Modify: `frontend/src/pages/Profile.tsx`
- Modify: `frontend/src/__tests__/Profile.test.tsx`

The button renders in the `Profile` component just below `<Header>`, NOT inside `Header` (Header stays presentational). It only appears on the normal render path, never on the `NotFoundView` early-return.

- [ ] **Step 1: Write the failing tests — append to `Profile.test.tsx`**

Add these inside the top-level `describe('Profile page', ...)` block (after the existing `describe` groups, before its closing brace). Also add a `localStorage` cleanup to the existing top-level `afterEach` — find the current `afterEach(() => { globalThis.fetch = originalFetch; vi.clearAllMocks(); });` and add `window.localStorage.clear();` as the first line inside it.

```tsx
  describe('"Make this me" button', () => {
    it('shows "Make this me" when no current user is set', async () => {
      globalThis.fetch = routedMock(summaryMocks());

      renderAt('/u/alice');

      expect(
        await screen.findByRole('button', { name: /make this me/i }),
      ).toBeInTheDocument();
    });

    it('clicking it persists the username and flips to "This is you"', async () => {
      globalThis.fetch = routedMock(summaryMocks());

      renderAt('/u/alice');

      const btn = await screen.findByRole('button', { name: /make this me/i });
      fireEvent.click(btn);

      expect(window.localStorage.getItem('synzoia.currentUser')).toBe('alice');
      expect(
        await screen.findByRole('button', { name: /this is you/i }),
      ).toBeDisabled();
    });

    it('shows a disabled "This is you" when viewing your saved profile', async () => {
      window.localStorage.setItem('synzoia.currentUser', 'alice');
      globalThis.fetch = routedMock(summaryMocks());

      renderAt('/u/alice');

      const btn = await screen.findByRole('button', { name: /this is you/i });
      expect(btn).toBeDisabled();
    });
  });
```

This uses `fireEvent`, which must be imported. At the top of `Profile.test.tsx` the import is currently `import { render, screen, waitFor } from '@testing-library/react';` — change it to include `fireEvent`:

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
```

- [ ] **Step 2: Run the tests, expect failure**

Run: `cd frontend && npm test -- --run Profile.test`
Expected: the 3 new tests FAIL (no button with that text yet). Existing Profile tests still pass.

- [ ] **Step 3: Add the import and button to `Profile.tsx`**

Add the hook import alongside the other imports near the top of `frontend/src/pages/Profile.tsx`:

```tsx
import { useCurrentUser } from '@/hooks/useCurrentUser';
```

RULES OF HOOKS: `useCurrentUser()` must be called unconditionally on every render, so it goes with the other hook calls — specifically immediately after the `summary` `useQuery(...)` call and BEFORE the `if (!username)` and `if (summary.error ...)` early returns. Add this line there:

```tsx
  const { currentUser, setCurrentUser } = useCurrentUser();
```

For reference, the top of `Profile()` should read in this order: `useParams` → `useSearchParams` → `const active = ...` → `summary = useQuery(...)` → `const { currentUser, setCurrentUser } = useCurrentUser();` → `if (!username) return ...` → `if (summary.error ...) return ...` → `return ( ...main tree... )`.

Then, in the returned JSX, insert the button immediately after `<Header ... />`:

```tsx
      <Header
        username={summary.data?.username ?? username}
        joinDate={summary.data?.join_date}
      />
      {currentUser === username ? (
        <Button variant="secondary" disabled>
          ✓ This is you
        </Button>
      ) : (
        <Button variant="primary" onClick={() => setCurrentUser(username)}>
          Make this me
        </Button>
      )}
      <TabStrip tabs={[...TABS]} defaultKey="summary" />
```

`Button` is already imported in `Profile.tsx` (used by `NotFoundView`/`ErrorView`). No new button import needed.

- [ ] **Step 4: Run the tests, expect pass**

Run: `cd frontend && npm test -- --run Profile.test`
Expected: all Profile tests pass (existing + 3 new).

- [ ] **Step 5: Run the full suite + type-check**

Run: `cd frontend && npm test -- --run` then `cd frontend && npx tsc --noEmit`
Expected: all green; tsc clean. Test count up by 8 from baseline (5 hook + 3 button).

## Task 3: Commit 1

- [ ] **Step 1: Stage and commit**

```bash
git add frontend/src/hooks/useCurrentUser.ts \
        frontend/src/hooks/__tests__/useCurrentUser.test.ts \
        frontend/src/pages/Profile.tsx \
        frontend/src/__tests__/Profile.test.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): useCurrentUser hook + "make this me" button

Adds a client-side current-user pointer stored in localStorage
(key synzoia.currentUser), with a synzoia:currentuser CustomEvent so
every hook instance stays in sync within a tab (plus cross-tab via
the native storage event). The per-user profile page gains a
"Make this me" button that saves the username, flipping to a
disabled "✓ This is you" on your own saved profile. No backend.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 2: Confirm**

Run: `git log --oneline -1`
Expected: the commit shows on top of `184ba23 docs(spec): ...`.

---

# Commit 2 — profile icon

## Task 4: Profile icon in header + mobile pill

**Files:**
- Modify: `frontend/src/components/layout/AppLayout.tsx`
- Test: `frontend/src/__tests__/AppLayout.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/AppLayout.test.tsx`:

```tsx
import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={['/feed']}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/feed" element={<div>feed body</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  window.localStorage.clear();
});

describe('AppLayout profile icon', () => {
  it('links to /users when no current user is set', () => {
    renderLayout();
    const links = screen.getAllByRole('link', { name: /your profile/i });
    // Header link + mobile pill link both point at /users.
    expect(links.length).toBeGreaterThanOrEqual(1);
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/users');
    }
  });

  it('links to /u/<name> when a current user is set', () => {
    window.localStorage.setItem('synzoia.currentUser', 'alice');
    renderLayout();
    const links = screen.getAllByRole('link', { name: /your profile/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/u/alice');
    }
  });
});
```

Note: both the header icon and the mobile "Me" pill carry the same `aria-label="Your profile"`, so `getAllByRole` finds both. jsdom renders both regardless of the CSS `sm:hidden` / `hidden sm:flex` breakpoints (CSS visibility isn't computed in jsdom), so asserting over all matches is correct.

- [ ] **Step 2: Run the test, expect failure**

Run: `cd frontend && npm test -- --run AppLayout.test`
Expected: FAIL — no element with accessible name "Your profile" yet.

- [ ] **Step 3: Implement the icon in `AppLayout.tsx`**

Add `CircleUser` to the lucide import (line 2):

```tsx
import { CircleUser, Database, Rss, Trophy, Users } from 'lucide-react';
```

Add the hook import below the ThemeToggle import (line 4):

```tsx
import { useCurrentUser } from '@/hooks/useCurrentUser';
```

Inside `AppLayout()`, compute the destination at the top of the function body (before the `return`):

```tsx
export function AppLayout() {
  const { currentUser } = useCurrentUser();
  const profileTarget = currentUser
    ? `/u/${encodeURIComponent(currentUser)}`
    : '/users';

  return (
```

In the header, add a `CircleUser` link between the `</nav>` and `<ThemeToggle />`:

```tsx
            </nav>
            <Link
              to={profileTarget}
              aria-label="Your profile"
              title="Your profile"
              className="text-muted-foreground hover:text-foreground transition-colors p-2 -m-2"
            >
              <CircleUser size={20} strokeWidth={1.75} />
            </Link>
            <ThemeToggle />
```

(`Link` is already imported at the top of `AppLayout.tsx`.)

In the mobile bottom pill, add a "Me" item after the Database `BottomNavItem`. Because `BottomNavItem` renders a `NavLink` without an `aria-label`, give the "Me" item a matching accessible name by passing the label "Me" — but the test queries `aria-label="Your profile"`, so add an explicit `aria-label` path. Update the `BottomNavItem` to accept an optional `ariaLabel` and apply it:

Change the `BottomNavItem` signature and `NavLink` to thread an optional aria-label:

```tsx
function BottomNavItem({
  to,
  icon,
  label,
  ariaLabel,
}: {
  to: string;
  icon: ReactNode;
  label: string;
  ariaLabel?: string;
}) {
  return (
    <NavLink
      to={to}
      end
      aria-label={ariaLabel}
      className={({ isActive }) =>
        `flex flex-col items-center justify-center gap-1 px-5 py-2 rounded-full transition-all ${
          isActive
            ? 'text-primary bg-[color-mix(in_oklch,var(--primary)_14%,transparent)]'
            : 'text-muted-foreground hover:text-foreground'
        }`
      }
    >
      <span aria-hidden="true">{icon}</span>
      <span className="text-[11px] font-medium tracking-wide">{label}</span>
    </NavLink>
  );
}
```

Then add the "Me" pill item after the Database item:

```tsx
          <BottomNavItem
            to="/db"
            icon={<Database size={18} strokeWidth={1.75} />}
            label="Database"
          />
          <BottomNavItem
            to={profileTarget}
            icon={<CircleUser size={18} strokeWidth={1.75} />}
            label="Me"
            ariaLabel="Your profile"
          />
```

- [ ] **Step 4: Run the test, expect pass**

Run: `cd frontend && npm test -- --run AppLayout.test`
Expected: 2 passed.

- [ ] **Step 5: Run the full suite + type-check**

Run: `cd frontend && npm test -- --run` then `cd frontend && npx tsc --noEmit`
Expected: all green; tsc clean. Existing `smoke.test.tsx` still passes (the new header/pill links don't change existing routes).

## Task 5: Commit 2

- [ ] **Step 1: Stage and commit**

```bash
git add frontend/src/components/layout/AppLayout.tsx \
        frontend/src/__tests__/AppLayout.test.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): profile icon in header + mobile nav

Adds a CircleUser link in the header top-right (all screen sizes) and
a "Me" item in the mobile bottom pill. Both resolve to /u/<currentUser>
once "Make this me" has been used, or /users beforehand so the user
can pick. Threads an optional aria-label through BottomNavItem so the
pill item is reachable by assistive tech and tests.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 2: Confirm**

Run: `git log --oneline -3`
Expected: two new feat commits on top of the spec commit.

---

# Final verification & push

## Task 6: Verify and push

- [ ] **Step 1: Full frontend suite**

Run: `cd frontend && npm test -- --run`
Expected: all green; +10 tests vs baseline (5 hook + 3 button + 2 layout) → ~63 total.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Push to the existing branch (updates PR #38)**

```bash
git push origin worktree-users-pages
```

Expected: the two new commits land on `worktree-users-pages`; PR #38 picks them up automatically. No new PR is created — confirm by noting the push output references the existing branch.

- [ ] **Step 4: Note for the human**

PR #38 now also contains the current-user feature. If the reviewer wants it isolated, it can be split into its own branch later — but since the button depends on the Profile page from the same PR, keeping them together is intentional.

---

## Spec coverage check

| Spec section | Plan task(s) |
|---|---|
| §2 useCurrentUser hook (localStorage + CustomEvent + storage sync) | Task 1 |
| §3 "Make this me" / "✓ This is you" button on Profile | Task 2 |
| §4 Profile icon — header + mobile pill, shared destination logic | Task 4 |
| §5 Testing (hook / Profile button / AppLayout) | Tasks 1, 2, 4 |
| §6 Out of scope | nothing built — respected (no /me route, no auth, no backend) |
| §7 Implementation order (two commits) | Task 3 (commit 1), Task 5 (commit 2) |
