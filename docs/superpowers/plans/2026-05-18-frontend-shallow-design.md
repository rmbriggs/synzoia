# Frontend Shallow Design Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn every route from a raw `<h1>` stub into a coherent product-shaped page using a small primitive library, shared `AppLayout` chrome, and a calm-minimal placeholder palette. Data-bearing sections show "coming soon" empty states; forms and navigation are real.

**Architecture:** Six small primitives in `src/components/ui/` (Card, PageHeader, Button, EmptyState, TabStrip, FormField). One layout shell in `src/components/layout/AppLayout.tsx` providing top bar + mobile bottom tab bar. `App.tsx` nests logged-in routes under `<Route element={<AppLayout/>}>`; `/auth` stays outside. Tailwind v4 with a deliberately empty `@theme` block — utility classes applied at component callsites.

**Tech Stack:** React 19, react-router-dom v7 (`<Outlet/>`, `<NavLink>`, `<Navigate>`, `useSearchParams`), Tailwind v4, Vitest + Testing Library.

**Spec:** [`docs/superpowers/specs/2026-05-18-frontend-shallow-design-design.md`](../specs/2026-05-18-frontend-shallow-design-design.md)

**Prerequisites:**
- Working directory: `/Users/micahbriggs/Developer/synzoia`
- On `main` (the scaffold from PR #1 is merged)
- Clean working tree
- Branch off `main` before starting: `git checkout -b feat/frontend-shallow-design`

**Conventions:**
- All paths relative to repo root.
- "Run from `frontend/`" means `cd frontend` first.
- Default exports for page and primitive components.
- Each task ends in a working state with a single commit; smoke test (`npm run test`) stays green throughout except inside Task 14 (where it's transiently red mid-task as part of TDD).

---

## Task 0: Branch off main

**Files:** none.

- [ ] **Step 1: Create + switch to the feature branch**

Run from repo root:

```bash
git checkout main
git pull
git checkout -b feat/frontend-shallow-design
```

Expected: switched to a new branch tracking nothing yet.

- [ ] **Step 2: Confirm clean state**

```bash
git status
```

Expected: `On branch feat/frontend-shallow-design — nothing to commit, working tree clean`.

---

## Task 1: Design tokens

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Replace `frontend/src/index.css`**

Replace the entire file with:

```css
@import "tailwindcss";

@theme {
  --color-background: oklch(99% 0.003 95);
  --radius-card: 1rem;
}

html,
body,
#root {
  height: 100%;
}

body {
  @apply bg-background text-slate-900 antialiased;
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", system-ui, sans-serif;
}
```

- [ ] **Step 2: Verify build + tests still pass**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: typecheck clean, lint clean, 11 tests pass.

- [ ] **Step 3: Commit**

Run from repo root:

```bash
git add frontend/src/index.css
git commit -m "feat(frontend): add placeholder design tokens"
```

---

## Task 2: Trivial primitives — Card, PageHeader, EmptyState

**Files:**
- Create: `frontend/src/components/ui/Card.tsx`
- Create: `frontend/src/components/ui/PageHeader.tsx`
- Create: `frontend/src/components/ui/EmptyState.tsx`

These three are pure JSX wrappers with no behavior, so no unit tests for them — the smoke test exercises them transitively once pages use them.

- [ ] **Step 1: Create `Card.tsx`**

```tsx
import type { ReactNode } from 'react';

interface CardProps {
  className?: string;
  children: ReactNode;
}

export default function Card({ className, children }: CardProps) {
  const base = 'bg-white border border-slate-200 rounded-2xl p-6';
  return <div className={className ? `${base} ${className}` : base}>{children}</div>;
}
```

- [ ] **Step 2: Create `PageHeader.tsx`**

```tsx
import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export default function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-slate-500 mt-1">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
```

- [ ] **Step 3: Create `EmptyState.tsx`**

```tsx
interface EmptyStateProps {
  message?: string;
}

export default function EmptyState({ message = 'Coming soon' }: EmptyStateProps) {
  return (
    <div className="py-12 text-center text-slate-500 text-sm">{message}</div>
  );
}
```

- [ ] **Step 4: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 11 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Card.tsx frontend/src/components/ui/PageHeader.tsx frontend/src/components/ui/EmptyState.tsx
git commit -m "feat(frontend): add Card, PageHeader, EmptyState primitives"
```

---

## Task 3: Button primitive (TDD)

**Files:**
- Create: `frontend/src/components/ui/Button.tsx`
- Create: `frontend/src/components/ui/__tests__/Button.test.tsx`

Button has two interesting behaviors worth testing: variant class branching, and the `to` prop switching the underlying element from `<button>` to react-router-dom's `<Link>`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/Button.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Button from '@/components/ui/Button';

describe('Button', () => {
  it('renders a <button> by default with primary variant classes', () => {
    const { container } = render(<Button variant="primary">Click</Button>);
    const btn = container.querySelector('button');
    expect(btn).not.toBeNull();
    expect(btn?.className).toContain('bg-indigo-600');
    expect(btn?.textContent).toBe('Click');
  });

  it('renders secondary variant with border + white background', () => {
    const { container } = render(<Button variant="secondary">Cancel</Button>);
    const btn = container.querySelector('button');
    expect(btn?.className).toContain('border-slate-200');
    expect(btn?.className).toContain('bg-white');
  });

  it('renders ghost variant', () => {
    const { container } = render(<Button variant="ghost">Skip</Button>);
    const btn = container.querySelector('button');
    expect(btn?.className).toContain('text-slate-600');
  });

  it('applies disabled styling when disabled prop is true', () => {
    const { container } = render(
      <Button variant="primary" disabled>Send</Button>,
    );
    const btn = container.querySelector('button');
    expect(btn?.disabled).toBe(true);
    expect(btn?.className).toContain('opacity-50');
    expect(btn?.className).toContain('cursor-not-allowed');
  });

  it('renders a react-router Link when `to` prop is provided', () => {
    const { container } = render(
      <MemoryRouter>
        <Button variant="primary" to="/somewhere">Go</Button>
      </MemoryRouter>,
    );
    const link = container.querySelector('a');
    expect(link).not.toBeNull();
    expect(link?.getAttribute('href')).toBe('/somewhere');
    expect(link?.className).toContain('bg-indigo-600');
    expect(container.querySelector('button')).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test and watch it fail**

Run from `frontend/`:

```bash
npm run test
```

Expected: failure — `Cannot find module '@/components/ui/Button'`.

- [ ] **Step 3: Implement `Button.tsx`**

Create `frontend/src/components/ui/Button.tsx`:

```tsx
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router-dom';

type Variant = 'primary' | 'secondary' | 'ghost';

interface ButtonBaseProps {
  variant: Variant;
  disabled?: boolean;
  className?: string;
  children: ReactNode;
}

interface ButtonAsButtonProps extends ButtonBaseProps {
  to?: undefined;
  type?: ButtonHTMLAttributes<HTMLButtonElement>['type'];
  onClick?: ButtonHTMLAttributes<HTMLButtonElement>['onClick'];
}

interface ButtonAsLinkProps extends ButtonBaseProps {
  to: string;
}

type ButtonProps = ButtonAsButtonProps | ButtonAsLinkProps;

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: 'bg-indigo-600 hover:bg-indigo-700 text-white',
  secondary: 'bg-white border border-slate-200 hover:bg-slate-50 text-slate-900',
  ghost: 'text-slate-600 hover:text-slate-900',
};

const BASE = 'inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition';
const DISABLED = 'opacity-50 cursor-not-allowed';

function composeClasses(variant: Variant, disabled: boolean, className?: string) {
  const parts = [BASE, VARIANT_CLASSES[variant]];
  if (disabled) parts.push(DISABLED);
  if (className) parts.push(className);
  return parts.join(' ');
}

export default function Button(props: ButtonProps) {
  const { variant, disabled = false, className, children } = props;
  const composed = composeClasses(variant, disabled, className);

  if ('to' in props && props.to !== undefined) {
    if (disabled) {
      return <span className={composed} aria-disabled="true">{children}</span>;
    }
    return <Link to={props.to} className={composed}>{children}</Link>;
  }

  return (
    <button
      type={props.type ?? 'button'}
      onClick={props.onClick}
      disabled={disabled}
      className={composed}
    >
      {children}
    </button>
  );
}
```

- [ ] **Step 4: Run the test and watch it pass**

Run from `frontend/`:

```bash
npm run test
```

Expected: 16 tests pass (4 in `client.test.ts`, 7 in `smoke.test.tsx`, 5 new in `Button.test.tsx`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Button.tsx frontend/src/components/ui/__tests__/Button.test.tsx
git commit -m "feat(frontend): add Button primitive with variant + Link branching"
```

---

## Task 4: FormField primitive

**Files:**
- Create: `frontend/src/components/ui/FormField.tsx`

Simple labeled input. No unit test — the prop wiring is straightforward and any page using it will surface bugs immediately.

- [ ] **Step 1: Create `FormField.tsx`**

```tsx
import type { InputHTMLAttributes } from 'react';

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  error?: string;
}

export default function FormField({ id, label, error, className, ...inputProps }: FormFieldProps) {
  const baseInput = 'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed';
  const inputClass = className ? `${baseInput} ${className}` : baseInput;
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 mb-1">
        {label}
      </label>
      <input id={id} className={inputClass} {...inputProps} />
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: typecheck + lint clean, 16 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/FormField.tsx
git commit -m "feat(frontend): add FormField primitive"
```

---

## Task 5: TabStrip primitive (TDD)

**Files:**
- Create: `frontend/src/components/ui/TabStrip.tsx`
- Create: `frontend/src/components/ui/__tests__/TabStrip.test.tsx`

TabStrip reads/writes `?tab=` via `useSearchParams`. Tested for active-tab highlighting and URL sync.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/ui/__tests__/TabStrip.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { MemoryRouter, useSearchParams } from 'react-router-dom';
import TabStrip from '@/components/ui/TabStrip';

const TABS = [
  { key: 'feed', label: 'Feed' },
  { key: 'leaderboard', label: 'Leaderboard' },
  { key: 'chat', label: 'Chat' },
];

// Probe component to inspect search params from inside the router.
function ParamSpy({ onParams }: { onParams: (s: URLSearchParams) => void }) {
  const [params] = useSearchParams();
  onParams(params);
  return null;
}

describe('TabStrip', () => {
  it('highlights the tab matching ?tab= in the URL', () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={['/crews/abc?tab=leaderboard']}>
        <TabStrip tabs={TABS} defaultKey="feed" />
      </MemoryRouter>,
    );
    expect(getByText('Leaderboard').className).toContain('border-indigo-600');
    expect(getByText('Feed').className).toContain('text-slate-500');
  });

  it('falls back to defaultKey when ?tab= is absent', () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={['/crews/abc']}>
        <TabStrip tabs={TABS} defaultKey="feed" />
      </MemoryRouter>,
    );
    expect(getByText('Feed').className).toContain('border-indigo-600');
  });

  it('writes ?tab= when a tab is clicked', () => {
    const captured: { current: URLSearchParams | null } = { current: null };
    const { getByText } = render(
      <MemoryRouter initialEntries={['/crews/abc']}>
        <TabStrip tabs={TABS} defaultKey="feed" />
        <ParamSpy onParams={(p) => { captured.current = p; }} />
      </MemoryRouter>,
    );
    fireEvent.click(getByText('Chat'));
    expect(captured.current?.get('tab')).toBe('chat');
  });
});
```

- [ ] **Step 2: Run the test and watch it fail**

Run from `frontend/`:

```bash
npm run test
```

Expected: failure — `Cannot find module '@/components/ui/TabStrip'`.

- [ ] **Step 3: Implement `TabStrip.tsx`**

Create `frontend/src/components/ui/TabStrip.tsx`:

```tsx
import { useSearchParams } from 'react-router-dom';

interface Tab {
  key: string;
  label: string;
}

interface TabStripProps {
  tabs: Tab[];
  defaultKey: string;
  paramName?: string;
}

export default function TabStrip({ tabs, defaultKey, paramName = 'tab' }: TabStripProps) {
  const [params, setParams] = useSearchParams();
  const active = params.get(paramName) ?? defaultKey;

  return (
    <div className="border-b border-slate-200 flex gap-6">
      {tabs.map((tab) => {
        const isActive = tab.key === active;
        const className = isActive
          ? 'pb-3 -mb-px border-b-2 border-indigo-600 text-slate-900 text-sm font-medium'
          : 'pb-3 -mb-px border-b-2 border-transparent text-slate-500 hover:text-slate-900 text-sm font-medium';
        return (
          <button
            key={tab.key}
            type="button"
            className={className}
            onClick={() => {
              const next = new URLSearchParams(params);
              next.set(paramName, tab.key);
              setParams(next, { replace: false });
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run the test and watch it pass**

Run from `frontend/`:

```bash
npm run test
```

Expected: 19 tests pass (16 prior + 3 new TabStrip).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/TabStrip.tsx frontend/src/components/ui/__tests__/TabStrip.test.tsx
git commit -m "feat(frontend): add TabStrip primitive with URL param sync"
```

---

## Task 6: AppLayout shell

**Files:**
- Create: `frontend/src/components/layout/AppLayout.tsx`

Smoke test will cover AppLayout transitively once routes are nested under it in Task 7. No dedicated unit test.

- [ ] **Step 1: Create `AppLayout.tsx`**

```tsx
import { Link, NavLink, Outlet } from 'react-router-dom';

export default function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-background border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/crews" className="text-lg font-semibold tracking-tight">
            synzoia
          </Link>
          <Link
            to="/settings"
            className="hidden sm:inline text-sm text-slate-600 hover:text-slate-900"
          >
            Settings
          </Link>
        </div>
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto px-4 sm:px-6 py-6 pb-24 sm:pb-6">
        <Outlet />
      </main>

      <nav
        className="sm:hidden fixed bottom-0 inset-x-0 bg-white border-t border-slate-200 flex"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <NavLink
          to="/crews"
          className={({ isActive }) =>
            `flex-1 py-3 text-center text-sm font-medium ${
              isActive ? 'text-indigo-600' : 'text-slate-500'
            }`
          }
        >
          Crews
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `flex-1 py-3 text-center text-sm font-medium ${
              isActive ? 'text-indigo-600' : 'text-slate-500'
            }`
          }
        >
          Settings
        </NavLink>
      </nav>
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass. (AppLayout isn't rendered yet by any route, so tests don't reach it.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/AppLayout.tsx
git commit -m "feat(frontend): add AppLayout shell (top bar + mobile tab bar)"
```

---

## Task 7: Restructure App.tsx routes under AppLayout

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Replace `App.tsx`**

Replace the entire file with:

```tsx
import { Route, Routes } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import Home from '@/pages/Home';
import Auth from '@/pages/Auth';
import Crews from '@/pages/Crews';
import CrewDetail from '@/pages/CrewDetail';
import PostSleep from '@/pages/PostSleep';
import UserProfile from '@/pages/UserProfile';
import Settings from '@/pages/Settings';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/auth" element={<Auth />} />
      <Route element={<AppLayout />}>
        <Route path="/crews" element={<Crews />} />
        <Route path="/crews/:id" element={<CrewDetail />} />
        <Route path="/crews/:id/post" element={<PostSleep />} />
        <Route path="/users/:id" element={<UserProfile />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 2: Verify smoke test still passes**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass. The smoke test renders each route and finds an `<h1>` from the existing stub pages — AppLayout wraps them now, but the h1 inside the stubs is still in the rendered tree.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): nest logged-in routes under AppLayout"
```

---

## Task 8: Rewrite `Settings.tsx`

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Replace `Settings.tsx`**

Replace the entire file with:

```tsx
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import FormField from '@/components/ui/FormField';
import PageHeader from '@/components/ui/PageHeader';

export default function Settings() {
  return (
    <>
      <PageHeader title="Settings" />
      <Card className="mt-6 space-y-4">
        <h2 className="text-lg font-semibold">Profile</h2>
        <FormField id="display-name" label="Display name" disabled />
        <FormField id="timezone" label="Timezone" disabled />
        <Button variant="primary" disabled>Save</Button>
      </Card>
      <Card className="mt-4">
        <h2 className="text-lg font-semibold">Sign out</h2>
        <p className="text-slate-500 text-sm mt-1">
          Sign out of synzoia on this device.
        </p>
        <Button variant="secondary" className="mt-3" disabled>Sign out</Button>
      </Card>
      <Card className="mt-4">
        <h2 className="text-lg font-semibold">About</h2>
        <p className="text-slate-500 text-sm mt-1">
          synzoia v0.0 — built for UATX Software Engineering Spring 2026.
        </p>
      </Card>
    </>
  );
}
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat(frontend): redesign /settings with shallow placeholder UI"
```

---

## Task 9: Rewrite `UserProfile.tsx`

**Files:**
- Modify: `frontend/src/pages/UserProfile.tsx`

- [ ] **Step 1: Replace `UserProfile.tsx`**

```tsx
import { useParams } from 'react-router-dom';
import Card from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';

export default function UserProfile() {
  const { id } = useParams<{ id: string }>();
  return (
    <>
      <PageHeader
        title={`User ${id}`}
        description="Real display name lands when backend's ready."
      />
      <Card className="mt-6">
        <h2 className="text-lg font-semibold">Streaks</h2>
        <EmptyState message="Current and longest streak appear here." />
      </Card>
      <Card className="mt-4">
        <h2 className="text-lg font-semibold">Recent posts</h2>
        <EmptyState message="Recent posts from crews you share will appear here." />
      </Card>
    </>
  );
}
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/UserProfile.tsx
git commit -m "feat(frontend): redesign /users/:id with shallow placeholder UI"
```

---

## Task 10: Rewrite `PostSleep.tsx`

**Files:**
- Modify: `frontend/src/pages/PostSleep.tsx`

- [ ] **Step 1: Replace `PostSleep.tsx`**

```tsx
import { useParams } from 'react-router-dom';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import FormField from '@/components/ui/FormField';
import PageHeader from '@/components/ui/PageHeader';

export default function PostSleep() {
  const { id } = useParams<{ id: string }>();
  return (
    <>
      <PageHeader
        title="Post your sleep"
        description="How'd you sleep last night?"
      />
      <Card className="mt-6 space-y-4">
        <FormField id="bedtime" label="Bedtime" type="datetime-local" disabled />
        <FormField id="wake" label="Wake time" type="datetime-local" disabled />
        <FormField
          id="quality"
          label="Quality (1–100)"
          type="number"
          min={1}
          max={100}
          disabled
        />
        <FormField
          id="note"
          label="Note (optional, up to 280 chars)"
          type="text"
          disabled
        />
        <div className="flex gap-3 pt-2">
          <Button variant="primary" disabled>Post</Button>
          <Button variant="ghost" to={`/crews/${id}`}>Cancel</Button>
        </div>
      </Card>
    </>
  );
}
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/PostSleep.tsx
git commit -m "feat(frontend): redesign /crews/:id/post with form placeholders"
```

---

## Task 11: Rewrite `Crews.tsx`

**Files:**
- Modify: `frontend/src/pages/Crews.tsx`

- [ ] **Step 1: Replace `Crews.tsx`**

```tsx
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';

export default function Crews() {
  return (
    <>
      <PageHeader
        title="Your crews"
        description="Private groups where you post your sleep."
      />
      <div className="mt-6 flex gap-3">
        <Button variant="primary" disabled>Create a crew</Button>
        <Button variant="secondary" disabled>Join with code</Button>
      </div>
      <Card className="mt-6">
        <EmptyState message="No crews yet. Coming soon." />
      </Card>
    </>
  );
}
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Crews.tsx
git commit -m "feat(frontend): redesign /crews with shallow placeholder UI"
```

---

## Task 12: Rewrite `Auth.tsx`

**Files:**
- Modify: `frontend/src/pages/Auth.tsx`

`/auth` does NOT use AppLayout (per Task 7's route structure). It renders a full-bleed centered card. The wordmark is wrapped in `<h1>` so the smoke test's h1-per-route assertion stays satisfied.

- [ ] **Step 1: Replace `Auth.tsx`**

```tsx
import { useState } from 'react';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import FormField from '@/components/ui/FormField';

export default function Auth() {
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>('sign-in');
  const isSignUp = mode === 'sign-up';

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="max-w-sm w-full">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">synzoia</h1>
          <p className="text-slate-500 text-sm mt-1">Sleep with friends.</p>
        </div>
        <div className="space-y-3 mt-6">
          {isSignUp && (
            <FormField id="display-name" label="Display name" type="text" />
          )}
          <FormField id="email" label="Email" type="email" />
          <FormField id="password" label="Password" type="password" />
        </div>
        <Button variant="primary" className="w-full mt-4" disabled>
          {isSignUp ? 'Sign up' : 'Sign in'}
        </Button>
        <p className="text-center text-sm text-slate-500 mt-4">
          {isSignUp ? 'Already have one?' : "Don't have an account?"}{' '}
          <button
            type="button"
            className="text-indigo-600 hover:underline font-medium"
            onClick={() => setMode(isSignUp ? 'sign-in' : 'sign-up')}
          >
            {isSignUp ? 'Sign in' : 'Sign up'}
          </button>
        </p>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass. The smoke test for `/auth` finds the new `<h1>` element.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Auth.tsx
git commit -m "feat(frontend): redesign /auth with centered card + mode toggle"
```

---

## Task 13: Rewrite `CrewDetail.tsx`

**Files:**
- Modify: `frontend/src/pages/CrewDetail.tsx`

- [ ] **Step 1: Replace `CrewDetail.tsx`**

```tsx
import { useParams, useSearchParams } from 'react-router-dom';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import TabStrip from '@/components/ui/TabStrip';

const TABS = [
  { key: 'feed', label: 'Feed' },
  { key: 'leaderboard', label: 'Leaderboard' },
  { key: 'chat', label: 'Chat' },
];

const TAB_MESSAGES: Record<string, string> = {
  feed: 'Feed coming soon — posts from this crew will appear here.',
  leaderboard: 'Leaderboard coming soon — weekly rankings.',
  chat: 'Chat coming soon — group thread for this crew.',
};

export default function CrewDetail() {
  const { id } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const activeTab = params.get('tab') ?? 'feed';
  const message = TAB_MESSAGES[activeTab] ?? TAB_MESSAGES.feed;

  return (
    <>
      <PageHeader
        title={`Crew ${id}`}
        description="Real crew name lands when backend's ready."
        action={
          <Button variant="primary" to={`/crews/${id}/post`}>
            Post sleep
          </Button>
        }
      />
      <div className="mt-6">
        <TabStrip tabs={TABS} defaultKey="feed" />
      </div>
      <Card className="mt-6">
        <EmptyState message={message} />
      </Card>
    </>
  );
}
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/CrewDetail.tsx
git commit -m "feat(frontend): redesign /crews/:id with tab strip + empty states"
```

---

## Task 14: Home redirect + smoke test update (TDD)

**Files:**
- Modify: `frontend/src/__tests__/smoke.test.tsx`
- Modify: `frontend/src/pages/Home.tsx`

This is the only task where the smoke test goes red briefly. Order: update the test first, watch it fail (because Home still has an h1 and no redirect), then update Home to redirect, watch it pass.

- [ ] **Step 1: Update the smoke test to expect Home as a redirect**

Replace `frontend/src/__tests__/smoke.test.tsx` entirely with:

```tsx
import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '@/App';

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
    },
  },
}));

vi.mock('@/hooks/useAuthSession', () => ({
  useAuthSession: () => ({ session: null, loading: false }),
}));

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('App smoke', () => {
  const routes = [
    '/auth',
    '/crews',
    '/crews/abc',
    '/crews/abc/post',
    '/users/xyz',
    '/settings',
  ];

  for (const route of routes) {
    it(`renders an <h1> at ${route}`, () => {
      const { container } = renderAt(route);
      const headings = container.querySelectorAll('h1');
      expect(headings.length).toBeGreaterThanOrEqual(1);
    });
  }

  it('redirects "/" to /auth when logged out', () => {
    const { container } = renderAt('/');
    // The "Sleep with friends." tagline only exists on /auth, so seeing it
    // here proves we actually redirected (vs. rendering Home directly).
    expect(container.textContent).toContain('Sleep with friends.');
  });
});
```

- [ ] **Step 2: Run the test and watch the redirect case fail**

Run from `frontend/`:

```bash
npm run test
```

Expected: 18 tests pass + 1 fail. The redirect test fails because the current `Home.tsx` (rewritten by no prior task) still renders its scaffolded `<h1>synzoia</h1>` + the `/ — landing / redirect (TBD)` paragraph; the `/auth` page is never reached, so the tagline isn't in the rendered output.

- [ ] **Step 3: Update `Home.tsx` to redirect**

Replace `frontend/src/pages/Home.tsx` entirely with:

```tsx
import { Navigate } from 'react-router-dom';
import { useAuthSession } from '@/hooks/useAuthSession';

export default function Home() {
  const { session, loading } = useAuthSession();
  if (loading) {
    return <p className="p-6">Loading…</p>;
  }
  return <Navigate to={session ? '/crews' : '/auth'} replace />;
}
```

- [ ] **Step 4: Run the tests and watch them all pass**

Run from `frontend/`:

```bash
npm run test
```

Expected: 19 tests pass (4 `client.test.ts` + 5 `Button.test.tsx` + 3 `TabStrip.test.tsx` + 6 `smoke.test.tsx` h1 + 1 redirect).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Home.tsx frontend/src/__tests__/smoke.test.tsx
git commit -m "feat(frontend): Home redirects based on auth session"
```

---

## Task 15: Manual acceptance walkthrough

**Files:** none modified. This verifies the spec's §9 acceptance checks end-to-end.

- [ ] **Step 1: Run the full verification suite**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test && npm run build
```

Expected: all four exit 0; `dist/` is produced.

- [ ] **Step 2: Start the dev server and walk through routes**

Run from `frontend/`:

```bash
npm run dev
```

In a browser (the port varies — check the terminal output), confirm:

- `/` redirects to `/auth` (since `useAuthSession` returns null).
- `/auth` shows a centered card with the "synzoia" wordmark + "Sleep with friends." tagline + email/password fields + a disabled "Sign in" button. Clicking "Sign up" toggles to a 3-field form. No top bar, no bottom tab bar.
- `/crews` shows the top bar (wordmark on left, "Settings" on right on desktop widths) and page content "Your crews" + two disabled action buttons + a "Coming soon" empty state.
- `/crews/abc` shows page header "Crew abc" + an active "Post sleep" button + a TabStrip (Feed/Leaderboard/Chat). Clicking each tab updates `?tab=` in the URL and swaps the empty-state message.
- Clicking the "Post sleep" button navigates to `/crews/abc/post`, which shows the disabled form. The ghost "Cancel" button navigates back to `/crews/abc`.
- `/users/xyz` shows "User xyz" + two empty-state cards.
- `/settings` shows three cards: Profile (disabled form + Save), Sign out (disabled button), About (static text).
- On mobile widths (DevTools 375px): top bar still visible, "Settings" hidden from top bar, a bottom tab bar appears with Crews | Settings.
- Every disabled button has 50% opacity and `not-allowed` cursor.

Stop the dev server (Ctrl-C).

- [ ] **Step 3: Confirm clean working tree**

Run from repo root:

```bash
git status
```

Expected: `On branch feat/frontend-shallow-design — nothing to commit, working tree clean`.

---

## Done

After Task 15, the branch `feat/frontend-shallow-design` contains the full shallow design pass. Final step is up to the user — either fast-forward to `main`, open another PR, or stack more work on top.
