# synzoia frontend — Dev-only auth bypass

**Date**: 2026-05-19
**Owner**: Micah
**Scope**: A localStorage-backed fake auth flow gated by `VITE_DEV_FAKE_AUTH=true`. Lets Micah click through the whole app while teammates build the real backend + schema. Designed for easy deletion when real Supabase Auth lands.
**Parent specs**:
- Project design: [`2026-05-16-synzoia-design.md`](./2026-05-16-synzoia-design.md)
- Shallow design pass: [`2026-05-18-frontend-shallow-design-design.md`](./2026-05-18-frontend-shallow-design-design.md)

---

## 1. Goal

After the shallow-design pass, every page renders but no one can stay logged in (the existing `useAuthSession` stub returns `{session: null}` always, so `/` redirects to `/auth` and `/auth`'s buttons are disabled). This pass adds a development-mode escape hatch so Micah can:

1. Visit `/auth`, fill any email + password, click "Sign in"
2. Get redirected to `/crews` with a session that survives page reloads
3. Navigate all 7 routes normally
4. Click "Sign out" from `/settings` to clear the session and return to `/auth`

No real Supabase Auth calls. No real user records. Purely a localStorage trick for unblocking frontend iteration while the backend is still being built.

**Out of scope (handled when real auth lands):**
- Email/password validation against Supabase
- Email confirmation flow
- Password reset
- OAuth providers
- Session refresh / expiry handling
- The actual real-auth implementation of `useAuthSession`

## 2. Activation

The dev bypass is gated by a single env var: `VITE_DEV_FAKE_AUTH=true`.

- When set, `useAuthSession` returns the localStorage-backed session, the Sign in button accepts any input, and Sign out is enabled.
- When unset (or any other value), the system behaves exactly as it did before this pass: `useAuthSession` returns `{session: null, loading: false}`, all auth buttons are disabled, and no localStorage reads happen.

The flag is declared in `frontend/.env.example` so anyone cloning the repo sees it. Production builds will simply not set it.

## 3. The `auth-dev` module

A single file at `src/lib/auth-dev.ts` containing:

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
  // Same-tab: our custom event
  window.addEventListener(CHANGE_EVENT, handler);
  // Cross-tab: native storage event
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

**Why a custom event + native storage event:** `localStorage` doesn't fire its `storage` event on the same tab that wrote it, only on *other* tabs. So we need our own event for same-tab subscribers (the `useAuthSession` hook), plus the native event for the rare case where someone has the app open in multiple tabs.

**Why `isEnabled` gates `read`:** safety. Even if `VITE_DEV_FAKE_AUTH` gets unset later, leftover localStorage data won't get returned as a session.

## 4. `useAuthSession` rewrite

Replace the current stub at `src/hooks/useAuthSession.ts`:

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

**Type change:** the hook's session type goes from `Session | null` (from `@supabase/supabase-js`) to `DevSession | null` (our own). Currently the only consumer reading it is `Home.tsx`, which uses it as a truthy check. No imports of the old `Session` type from `useAuthSession`'s consumers break, because there weren't any.

When real Supabase Auth lands, this hook becomes the merge point — it'll likely return a unified `AuthSession` type that covers both dev and real-auth shapes, or just use the real `Session` and the dev module's structure mirrors it more closely.

## 5. `Auth.tsx` changes

The page currently has a disabled "Sign in" / "Sign up" button. Changes:

- Add `import { devAuth } from '@/lib/auth-dev'` and `import { useNavigate } from 'react-router-dom'`.
- Track form state: `email`, `password`, `displayName` (only used in sign-up mode).
- Make the form a real `<form>` element with `onSubmit`.
- The submit handler:
  ```ts
  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!devAuth.isEnabled()) return;          // no-op if flag off
    if (!email || !password) return;           // basic guard
    if (isSignUp && !displayName) return;
    const effectiveName = displayName || email.split('@')[0];
    devAuth.signIn(effectiveName, email);
    navigate('/crews');
  }
  ```
- The primary button is `disabled` ONLY when `!devAuth.isEnabled()`. When the flag is on, it's enabled and submits the form.
- The `FormField` components get controlled-value props (`value` + `onChange`) so the form actually captures input.
- Add a small "Dev mode" pill above the wordmark — visible only when `devAuth.isEnabled()`. Sketch:
  ```tsx
  {devAuth.isEnabled() && (
    <div className="text-center mb-3">
      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
        Dev mode
      </span>
    </div>
  )}
  ```
  Style: amber pill on a centered line. Makes it visually obvious you're in fake-auth mode and not real auth.

The mode toggle (Sign in ↔ Sign up) keeps working as before.

## 6. `Settings.tsx` changes

The page has a disabled "Sign out" button. Changes:

- Add `import { devAuth } from '@/lib/auth-dev'`, `import { useAuthSession } from '@/hooks/useAuthSession'`, `import { useNavigate } from 'react-router-dom'`.
- Read the current session via `useAuthSession()`.
- The Sign out button is `disabled` when there's no session OR when the dev flag is off; otherwise enabled.
- The button's `onClick`:
  ```ts
  function onSignOut() {
    devAuth.signOut();
    navigate('/auth');
  }
  ```

The Profile card's "Save" button stays disabled — saving a profile requires a backend.

The About card optionally adds a one-line note when in dev mode: "Running in dev-fake-auth mode." Helps remind the user that what they see isn't backed by real data.

## 7. Env var declaration

`src/vite-env.d.ts` gets a new field:

```ts
interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string | undefined;
  readonly VITE_SUPABASE_ANON_KEY: string | undefined;
  readonly VITE_API_BASE_URL: string | undefined;
  readonly VITE_DEV_FAKE_AUTH: string | undefined;
}
```

`frontend/.env.example` gets a section explaining it:

```
# Dev-only: when set to "true", the frontend uses a localStorage-backed
# fake auth flow so you can navigate the app before real auth is wired.
# Leave unset (or any other value) in production. See
# docs/superpowers/specs/2026-05-19-frontend-dev-auth-bypass-design.md.
VITE_DEV_FAKE_AUTH=true
```

Including `=true` in the example is deliberate: anyone cloning the repo with no backend yet wants this on. They can flip it off when real auth lands.

## 8. Testing impact

The existing smoke test mocks `@/hooks/useAuthSession` directly to return `{session: null, loading: false}`. That mock is unaffected by the rewrite — the test doesn't reach the new module.

The redirect test (`redirects "/" to /auth when logged out`) still works because the mock returns `null`.

**Not added:** unit tests for `auth-dev.ts`. The module is throwaway code (deleted when real Supabase Auth lands), and the round-trips it performs (localStorage read/write/subscribe) don't catch the kind of bug worth a test — typical failures here are forgetting to wire something up, which surfaces immediately on manual click-through.

## 9. File structure

```
frontend/src/
├── lib/
│   └── auth-dev.ts            # NEW
├── hooks/
│   └── useAuthSession.ts      # rewritten
├── pages/
│   ├── Auth.tsx               # form wires up + Dev-mode pill
│   └── Settings.tsx           # Sign out wires up
└── vite-env.d.ts              # +VITE_DEV_FAKE_AUTH

frontend/.env.example          # +VITE_DEV_FAKE_AUTH=true documented
```

## 10. Acceptance checks

After this lands:

1. `npm run typecheck`, `npm run lint`, `npm run test` (19 tests) all exit 0.
2. `npm run build` produces `dist/`.
3. With `VITE_DEV_FAKE_AUTH=true` in `.env.local`:
   - Visiting `/` redirects to `/auth` when no session exists.
   - On `/auth`, the Sign in button is enabled. Submitting with any email + password navigates to `/crews`.
   - Reloading the page on `/crews` keeps you on `/crews` (session survives reload).
   - All 7 routes are navigable. Top bar + bottom tab bar (mobile) work as before.
   - On `/settings`, the Sign out button is enabled. Clicking it returns you to `/auth` and reloading `/crews` from there redirects you back to `/auth`.
   - A "Dev mode" pill is visible on the `/auth` card.
4. With `VITE_DEV_FAKE_AUTH` unset:
   - The Sign in button is disabled.
   - `/auth` looks identical to the shallow-design state.
   - No localStorage entry is created.
5. With `VITE_DEV_FAKE_AUTH=true` AND a session stored, then `VITE_DEV_FAKE_AUTH` later unset:
   - The hook returns null session despite the localStorage entry being present.
   - User lands on `/auth` from `/` redirect.
   - No leftover behaviors from the previous session.

## 11. Cleanup plan (when real auth lands)

When the real Supabase Auth flow is built (separate spec, later):

1. Delete `src/lib/auth-dev.ts`.
2. Rewrite `src/hooks/useAuthSession.ts` to subscribe to `supabase.auth.onAuthStateChange`.
3. Rewrite `Auth.tsx` to call `supabase.auth.signInWithPassword` and `supabase.auth.signUp`.
4. Rewrite `Settings.tsx`'s sign-out handler to call `supabase.auth.signOut`.
5. Remove `VITE_DEV_FAKE_AUTH` from `.env.example` and `vite-env.d.ts`.

The footprint is small enough that the cleanup is one PR.
