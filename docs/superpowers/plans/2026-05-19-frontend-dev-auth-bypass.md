# Frontend Dev-Auth-Bypass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Micah click through the whole synzoia frontend by signing in with any email + password (localStorage-backed fake session) so he can iterate on UI while teammates build the backend.

**Architecture:** A single dev-only module (`src/lib/auth-dev.ts`) reads/writes a JSON session in `localStorage`, gated by `VITE_DEV_FAKE_AUTH=true`. `useAuthSession` subscribes to it; `Auth.tsx`'s form calls `signIn` on submit; `Settings.tsx`'s sign-out button calls `signOut`. Smoke test is unaffected (it mocks the hook directly).

**Tech Stack:** React 19, react-router-dom v7 (`useNavigate`), Vite env vars, `localStorage`, window events for same-tab + cross-tab session change notification.

**Spec:** [`docs/superpowers/specs/2026-05-19-frontend-dev-auth-bypass-design.md`](../specs/2026-05-19-frontend-dev-auth-bypass-design.md)

**Prerequisites:**
- Working directory: `/Users/micahbriggs/Developer/synzoia`
- On branch `feat/frontend-shallow-design` (the shallow-design pass branched off `main` and hasn't been merged yet — this work stacks on top, same branch, same eventual PR)
- Working tree clean
- 19 tests passing, typecheck + lint + build all clean

**Conventions:**
- All paths relative to repo root.
- "Run from `frontend/`" means `cd frontend` first.
- Each task ends with `npm run typecheck && npm run lint && npm run test` clean and a commit. Tests stay at 19 throughout.

---

## Task 1: Env var declaration + .env.example update

**Files:**
- Modify: `frontend/src/vite-env.d.ts`
- Modify: `frontend/.env.example`
- Modify: `frontend/.env.local` (locally, not committed — `.env.local` is gitignored)

- [ ] **Step 1: Add `VITE_DEV_FAKE_AUTH` to the env type**

Replace `frontend/src/vite-env.d.ts` with:

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string | undefined;
  readonly VITE_SUPABASE_ANON_KEY: string | undefined;
  readonly VITE_API_BASE_URL: string | undefined;
  readonly VITE_DEV_FAKE_AUTH: string | undefined;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

- [ ] **Step 2: Document the flag in `.env.example`**

Replace `frontend/.env.example` with:

```
# Supabase project URL — Settings → API in the Supabase dashboard.
VITE_SUPABASE_URL=https://your-project.supabase.co

# Supabase anon (public) key — safe to ship to the browser.
# DO NOT put the service role key here; that lives in the backend.
VITE_SUPABASE_ANON_KEY=your-anon-public-key

# FastAPI base URL.
#   - Local dev: http://localhost:8000
#   - Production: /api (FastAPI serves the bundle, same origin)
VITE_API_BASE_URL=http://localhost:8000

# Dev-only: when set to "true", the frontend uses a localStorage-backed
# fake auth flow so you can navigate the app before real auth is wired.
# Leave unset (or any other value) in production. See
# docs/superpowers/specs/2026-05-19-frontend-dev-auth-bypass-design.md.
VITE_DEV_FAKE_AUTH=true
```

- [ ] **Step 3: Add `VITE_DEV_FAKE_AUTH=true` to your local `.env.local`**

Run from `frontend/`:

```bash
grep -q '^VITE_DEV_FAKE_AUTH=' .env.local 2>/dev/null || printf '\nVITE_DEV_FAKE_AUTH=true\n' >> .env.local
cat .env.local | grep VITE_DEV_FAKE_AUTH
```

Expected: prints `VITE_DEV_FAKE_AUTH=true`.

(This file is gitignored, so the change is local-only and won't appear in `git status`.)

- [ ] **Step 4: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: typecheck clean (the new env var type is now declared), lint clean, 19 tests pass.

- [ ] **Step 5: Commit**

Run from repo root:

```bash
git add frontend/src/vite-env.d.ts frontend/.env.example
git commit -m "feat(frontend): declare VITE_DEV_FAKE_AUTH env var"
```

`.env.local` is gitignored and not part of the commit.

---

## Task 2: Create `auth-dev.ts` module

**Files:**
- Create: `frontend/src/lib/auth-dev.ts`

- [ ] **Step 1: Create the module**

Create `frontend/src/lib/auth-dev.ts`:

```ts
const KEY = 'synzoia.dev-session';
const CHANGE_EVENT = 'synzoia:dev-auth-change';

export interface DevSession {
  userId: string;
  displayName: string;
  email: string;
  signedInAt: number;
}

function isEnabled(): boolean {
  return import.meta.env.VITE_DEV_FAKE_AUTH === 'true';
}

function read(): DevSession | null {
  if (!isEnabled()) return null;
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as DevSession) : null;
  } catch {
    return null;
  }
}

function emit() {
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

function signIn(displayName: string, email: string): DevSession {
  const session: DevSession = {
    userId: crypto.randomUUID(),
    displayName,
    email,
    signedInAt: Date.now(),
  };
  localStorage.setItem(KEY, JSON.stringify(session));
  emit();
  return session;
}

function signOut(): void {
  localStorage.removeItem(KEY);
  emit();
}

function subscribe(callback: (s: DevSession | null) => void): () => void {
  const handler = () => callback(read());
  // Same-tab notifications come from our custom event (localStorage
  // doesn't fire 'storage' on the tab that wrote it).
  window.addEventListener(CHANGE_EVENT, handler);
  // Cross-tab notifications come from the native storage event.
  const storageHandler = (e: StorageEvent) => {
    if (e.key === KEY || e.key === null) handler();
  };
  window.addEventListener('storage', storageHandler);
  return () => {
    window.removeEventListener(CHANGE_EVENT, handler);
    window.removeEventListener('storage', storageHandler);
  };
}

export const devAuth = { isEnabled, read, signIn, signOut, subscribe };
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass. The new module isn't imported anywhere yet, so nothing has changed behaviorally.

- [ ] **Step 3: Commit**

Run from repo root:

```bash
git add frontend/src/lib/auth-dev.ts
git commit -m "feat(frontend): add dev-only auth module backed by localStorage"
```

---

## Task 3: Rewrite `useAuthSession` to subscribe to `devAuth`

**Files:**
- Modify: `frontend/src/hooks/useAuthSession.ts`

- [ ] **Step 1: Replace `useAuthSession.ts`**

Replace `frontend/src/hooks/useAuthSession.ts` entirely with:

```ts
import { useEffect, useState } from 'react';
import { devAuth, type DevSession } from '@/lib/auth-dev';

export interface AuthSessionState {
  session: DevSession | null;
  loading: boolean;
}

export function useAuthSession(): AuthSessionState {
  const [session, setSession] = useState<DevSession | null>(() => devAuth.read());

  useEffect(() => devAuth.subscribe(setSession), []);

  return { session, loading: false };
}
```

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass. The smoke test mocks `@/hooks/useAuthSession` directly, so it doesn't reach the rewritten implementation. `Home.tsx`'s consumer (which uses `session` only as a truthy check) is type-compatible with `DevSession | null`.

- [ ] **Step 3: Commit**

Run from repo root:

```bash
git add frontend/src/hooks/useAuthSession.ts
git commit -m "feat(frontend): wire useAuthSession to devAuth subscription"
```

---

## Task 4: Wire `Auth.tsx` form to `devAuth.signIn`

**Files:**
- Modify: `frontend/src/pages/Auth.tsx`

This task replaces the disabled-form stub with a working form. When the dev flag is on, submitting with any non-empty email + password calls `devAuth.signIn` and navigates to `/crews`. When the flag is off, the form's submit button stays disabled, exactly as before.

- [ ] **Step 1: Replace `Auth.tsx`**

Replace `frontend/src/pages/Auth.tsx` entirely with:

```tsx
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import FormField from '@/components/ui/FormField';
import { devAuth } from '@/lib/auth-dev';

export default function Auth() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>('sign-in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');

  const isSignUp = mode === 'sign-up';
  const devEnabled = devAuth.isEnabled();

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!devEnabled) return;
    if (!email || !password) return;
    if (isSignUp && !displayName) return;
    const effectiveName = isSignUp ? displayName : email.split('@')[0];
    devAuth.signIn(effectiveName, email);
    navigate('/crews');
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="max-w-sm w-full">
        {devEnabled && (
          <div className="text-center mb-3">
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
              Dev mode
            </span>
          </div>
        )}
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">synzoia</h1>
          <p className="text-slate-500 text-sm mt-1">Sleep with friends.</p>
        </div>
        <form className="space-y-3 mt-6" onSubmit={onSubmit}>
          {isSignUp && (
            <FormField
              id="display-name"
              label="Display name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          )}
          <FormField
            id="email"
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <FormField
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button
            variant="primary"
            className="w-full mt-4"
            type="submit"
            disabled={!devEnabled}
          >
            {isSignUp ? 'Sign up' : 'Sign in'}
          </Button>
        </form>
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

Key differences from the previous version:
- `useState` for `email`, `password`, `displayName` (the form is now controlled).
- `<form onSubmit={onSubmit}>` wraps the fields + submit button. Pressing Enter in any field also submits.
- Submit button now has `type="submit"` (it was implicit `type="button"` before).
- `disabled={!devEnabled}` instead of always `disabled`.
- "Dev mode" pill appears when `devAuth.isEnabled()`.
- `onSubmit` calls `devAuth.signIn` and navigates.

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass. The smoke test for `/auth` still finds the `<h1>synzoia</h1>` inside the card.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Auth.tsx
git commit -m "feat(frontend): wire Auth form to devAuth + show Dev mode pill"
```

---

## Task 5: Wire `Settings.tsx` sign-out button

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Replace `Settings.tsx`**

Replace `frontend/src/pages/Settings.tsx` entirely with:

```tsx
import { useNavigate } from 'react-router-dom';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import FormField from '@/components/ui/FormField';
import PageHeader from '@/components/ui/PageHeader';
import { useAuthSession } from '@/hooks/useAuthSession';
import { devAuth } from '@/lib/auth-dev';

export default function Settings() {
  const navigate = useNavigate();
  const { session } = useAuthSession();
  const devEnabled = devAuth.isEnabled();
  const canSignOut = devEnabled && session !== null;

  function onSignOut() {
    devAuth.signOut();
    navigate('/auth');
  }

  return (
    <>
      <PageHeader title="Settings" />
      <Card className="mt-6 space-y-4">
        <h2 className="text-lg font-semibold">Profile</h2>
        <FormField id="settings-display-name" label="Display name" disabled />
        <FormField id="settings-timezone" label="Timezone" disabled />
        <Button variant="primary" disabled>Save</Button>
      </Card>
      <Card className="mt-4">
        <h2 className="text-lg font-semibold">Sign out</h2>
        <p className="text-slate-500 text-sm mt-1">
          Sign out of synzoia on this device.
        </p>
        <Button
          variant="secondary"
          className="mt-3"
          disabled={!canSignOut}
          onClick={onSignOut}
        >
          Sign out
        </Button>
      </Card>
      <Card className="mt-4">
        <h2 className="text-lg font-semibold">About</h2>
        <p className="text-slate-500 text-sm mt-1">
          synzoia v0.0 — built for UATX Software Engineering Spring 2026.
        </p>
        {devEnabled && (
          <p className="text-xs text-amber-700 mt-2">
            Running in dev-fake-auth mode.
          </p>
        )}
      </Card>
    </>
  );
}
```

Key differences from the previous version:
- Reads `session` via `useAuthSession`.
- Sign out button enabled only when dev flag is on AND a session exists.
- `onSignOut` calls `devAuth.signOut()` then navigates to `/auth`.
- About card shows a small amber line ("Running in dev-fake-auth mode.") when the flag is on.

- [ ] **Step 2: Verify**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test
```

Expected: clean, 19 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat(frontend): wire Settings sign-out button to devAuth"
```

---

## Task 6: Manual acceptance walkthrough

**Files:** none modified. This task verifies the spec's §10 acceptance checks end-to-end.

- [ ] **Step 1: Confirm automated suite is green**

Run from `frontend/`:

```bash
npm run typecheck && npm run lint && npm run test && npm run build
```

Expected: all four exit 0; `dist/` is produced.

- [ ] **Step 2: Confirm `VITE_DEV_FAKE_AUTH=true` is in `.env.local`**

Run from `frontend/`:

```bash
grep VITE_DEV_FAKE_AUTH .env.local
```

Expected: `VITE_DEV_FAKE_AUTH=true`. If absent or set to anything else, fix it before continuing — without this flag the dev path is dormant by design and the rest of this task can't proceed.

- [ ] **Step 3: Start the dev server and walk through the flow**

Run from `frontend/`:

```bash
npm run dev
```

In the browser (port varies — read the terminal output), confirm each of these in order:

1. Visit `/`. You're redirected to `/auth`. The "Dev mode" amber pill is visible above the synzoia wordmark.
2. On `/auth`, the "Sign in" button is enabled. Type any email (e.g., `test@example.com`) and any password. Click Sign in. You land on `/crews`.
3. The top bar shows the synzoia wordmark and the Settings link (on desktop widths).
4. Visit `/`. You stay redirected to `/crews` because a session exists.
5. Reload `/crews`. You're still on `/crews` (session survived).
6. Click around: `/crews/abc`, `/crews/abc/post`, `/users/xyz`, `/settings`. Each page renders; navigation works.
7. On `/settings`, the About card shows "Running in dev-fake-auth mode." The Sign out button is enabled (you have a session).
8. Click Sign out. You land on `/auth`. The form is back to its empty state.
9. Visit `/` again. You're redirected to `/auth` (no session).

- [ ] **Step 4: Confirm the production-safety case**

Stop the dev server (Ctrl-C). Edit `frontend/.env.local` and either remove the `VITE_DEV_FAKE_AUTH` line or change it to `VITE_DEV_FAKE_AUTH=false`. Restart the dev server.

In the browser:

1. Visit `/auth`. The "Dev mode" pill is gone. The Sign in button is disabled.
2. Visit `/settings` directly (no AppLayout for `/auth`, but `/settings` is fine). The About card has no "Running in dev-fake-auth mode." line. The Sign out button is disabled.
3. Open DevTools → Application → Local Storage → your-dev-origin. If a `synzoia.dev-session` key exists from earlier testing, the app does NOT use it — visiting `/` still redirects to `/auth` because `devAuth.read()` returns `null` when `isEnabled()` is false. (You can manually delete the key if you want a clean state, but it's not required.)
4. Re-enable the flag (`VITE_DEV_FAKE_AUTH=true`) and restart the dev server before moving on. Note: if you had a leftover session in localStorage, you'll now be auto-signed-in.

- [ ] **Step 5: Final clean state**

Stop the dev server. Ensure `VITE_DEV_FAKE_AUTH=true` is set in `.env.local` for next time.

Run from repo root:

```bash
git status
```

Expected: clean working tree on `feat/frontend-shallow-design`.

---

## Done

After Task 6, the dev auth bypass is fully landed on `feat/frontend-shallow-design`. The branch now contains both the shallow-design pass and the dev-auth bypass. Push + PR is up to the user.
