# Frontend Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `frontend/` so all three synzoia teammates can `git pull && cd frontend && npm install && npm run dev` and immediately start building their UI slices in parallel.

**Architecture:** Vite + React 19 + TypeScript (strict) + Tailwind v4. Single Supabase client singleton, single React Query client, one `apiFetch` wrapper. React Router v7 in declarative mode with 7 stub pages. One Vitest smoke test that proves the toolchain wires together end-to-end.

**Tech Stack:** Vite, React, TypeScript, Tailwind v4 (`@tailwindcss/vite`), `react-router-dom` v7, `@tanstack/react-query` v5, `@supabase/supabase-js` v2, Vitest + Testing Library + jsdom, ESLint flat config, Prettier + `prettier-plugin-tailwindcss`.

**Spec:** [`docs/superpowers/specs/2026-05-17-frontend-scaffolding-design.md`](../specs/2026-05-17-frontend-scaffolding-design.md)

**Prerequisites:**
- Working directory: `/Users/micahbriggs/Developer/synzoia`
- Clean git working tree on `main`
- Node 20+ and npm 10+ installed
- No `frontend/` directory yet

**Conventions for this plan:**
- All paths are relative to the repo root unless otherwise stated.
- "Run from `frontend/`" means `cd frontend` first if you're not already there.
- Commit messages are imperative, short, follow existing repo style.
- Co-author trailer is omitted in this plan's example commands (add it per your usual workflow).

---

## Task 1: Bootstrap the project skeleton

**Files:**
- Create: `frontend/package.json` (via `npm init` + `npm pkg set`)
- Create: `frontend/.gitignore`
- Create: `frontend/README.md`

- [ ] **Step 1: Create the directory**

Run from repo root:

```bash
mkdir frontend
```

- [ ] **Step 2: Initialize package.json**

Run from `frontend/`:

```bash
npm init -y
```

Expected: creates `frontend/package.json` with placeholder defaults.

- [ ] **Step 3: Set project metadata and scripts**

Run from `frontend/`:

```bash
npm pkg set name="synzoia-frontend"
npm pkg set version="0.0.0"
npm pkg set private=true --json
npm pkg set type="module"
npm pkg set scripts.dev="vite"
npm pkg set scripts.build="tsc -b && vite build"
npm pkg set scripts.preview="vite preview"
npm pkg set scripts.test="vitest run"
npm pkg set scripts.test:watch="vitest"
npm pkg set scripts.lint="eslint ."
npm pkg set scripts.typecheck="tsc -b --noEmit"
npm pkg set scripts.format="prettier --write ."
```

Verify with `cat frontend/package.json` — `name`, `type: "module"`, and all eight scripts should be present.

- [ ] **Step 4: Create `.gitignore`**

Create `frontend/.gitignore`:

```
node_modules
dist
.env
.env.local
*.local

# Editor
.DS_Store
.vscode/*
!.vscode/extensions.json
.idea

# Test output
coverage
.vitest-cache

# TS incremental build cache
*.tsbuildinfo
```

- [ ] **Step 5: Create a placeholder README**

Create `frontend/README.md`:

```markdown
# synzoia frontend

React + TypeScript + Vite + Tailwind v4 frontend for synzoia.

## Running locally

```bash
npm install
cp .env.example .env.local      # then fill in your values
npm run dev
```

The dev server runs on `http://localhost:5173` by default.

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Type-check and produce `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run test` | One-shot Vitest run |
| `npm run test:watch` | Vitest in watch mode |
| `npm run lint` | ESLint over the whole project |
| `npm run typecheck` | `tsc -b --noEmit` |
| `npm run format` | Prettier write |

## Environment variables

See `.env.example`. The Supabase **service role key** lives in the backend, never here.

## Layout

See `docs/superpowers/specs/2026-05-17-frontend-scaffolding-design.md` at the repo root for the full design.
```

- [ ] **Step 6: Commit**

Run from repo root:

```bash
git add frontend/package.json frontend/.gitignore frontend/README.md
git commit -m "feat(frontend): bootstrap project skeleton"
```

---

## Task 2: Install runtime and dev dependencies

**Files:**
- Modify: `frontend/package.json` (npm updates it)
- Create: `frontend/package-lock.json` (committed)
- Create: `frontend/node_modules/` (gitignored)

- [ ] **Step 1: Install runtime dependencies**

Run from `frontend/`:

```bash
npm install \
  react \
  react-dom \
  react-router-dom \
  @tanstack/react-query \
  @supabase/supabase-js
```

Expected: `dependencies` block in `package.json` populated; `package-lock.json` created.

- [ ] **Step 2: Install dev dependencies**

Run from `frontend/`:

```bash
npm install -D \
  vite \
  @vitejs/plugin-react \
  typescript \
  @types/react \
  @types/react-dom \
  @types/node \
  tailwindcss \
  @tailwindcss/vite \
  vitest \
  @vitest/ui \
  jsdom \
  @testing-library/react \
  @testing-library/jest-dom \
  eslint \
  @eslint/js \
  typescript-eslint \
  eslint-plugin-react-hooks \
  eslint-plugin-react-refresh \
  globals \
  prettier \
  prettier-plugin-tailwindcss
```

Expected: `devDependencies` block populated; `package-lock.json` updated.

- [ ] **Step 3: Verify the dependency list**

Run from `frontend/`:

```bash
node -e "const p=require('./package.json'); console.log('deps:', Object.keys(p.dependencies).length, 'dev:', Object.keys(p.devDependencies).length)"
```

Expected: `deps: 5 dev: 21`

- [ ] **Step 4: Commit**

Run from repo root:

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): install runtime and dev dependencies"
```

---

## Task 3: TypeScript configuration

**Files:**
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`

- [ ] **Step 1: Create `tsconfig.json` (project references root)**

Create `frontend/tsconfig.json`:

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

- [ ] **Step 2: Create `tsconfig.app.json` (app code)**

Create `frontend/tsconfig.app.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,

    "paths": {
      "@/*": ["./src/*"]
    },

    "types": ["vite/client", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create `tsconfig.node.json` (for `vite.config.ts`)**

Create `frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,

    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,

    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Commit**

Run from repo root:

```bash
git add frontend/tsconfig.json frontend/tsconfig.app.json frontend/tsconfig.node.json
git commit -m "feat(frontend): add TypeScript project references config"
```

Note: typecheck isn't runnable yet because no source files or `vite.config.ts` exist. That comes in Task 4.

---

## Task 4: Vite + Vitest config, entry HTML, env types

**Files:**
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/vite-env.d.ts`

- [ ] **Step 1: Create `vite.config.ts`**

Create `frontend/vite.config.ts`:

```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
    css: true,
  },
});
```

- [ ] **Step 2: Create `index.html`**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>synzoia</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Create `src/vite-env.d.ts`**

Create `frontend/src/vite-env.d.ts`:

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

- [ ] **Step 4: Commit**

Run from repo root:

```bash
git add frontend/vite.config.ts frontend/index.html frontend/src/vite-env.d.ts
git commit -m "feat(frontend): add Vite + Vitest config, index.html, env types"
```

---

## Task 5: Tailwind CSS entry

**Files:**
- Create: `frontend/src/index.css`

- [ ] **Step 1: Create the global stylesheet**

Create `frontend/src/index.css`:

```css
@import "tailwindcss";

@theme {
  /* Visual identity tokens land here once Teammate B picks the palette + type scale
     (parent design spec §10.3). Empty for now is intentional — defaults to Tailwind's
     stock theme. */
}

html,
body,
#root {
  height: 100%;
}
```

- [ ] **Step 2: Commit**

Run from repo root:

```bash
git add frontend/src/index.css
git commit -m "feat(frontend): add Tailwind v4 CSS entry"
```

---

## Task 6: ESLint flat config + Prettier

**Files:**
- Create: `frontend/eslint.config.js`
- Create: `frontend/.prettierrc.json`
- Create: `frontend/.prettierignore`

- [ ] **Step 1: Create `eslint.config.js`**

Create `frontend/eslint.config.js`:

```js
import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'node_modules', 'coverage'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
    },
  },
);
```

- [ ] **Step 2: Create `.prettierrc.json`**

Create `frontend/.prettierrc.json`:

```json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

- [ ] **Step 3: Create `.prettierignore`**

Create `frontend/.prettierignore`:

```
node_modules
dist
coverage
package-lock.json
```

- [ ] **Step 4: Commit**

Run from repo root:

```bash
git add frontend/eslint.config.js frontend/.prettierrc.json frontend/.prettierignore
git commit -m "feat(frontend): add ESLint flat config and Prettier"
```

---

## Task 7: Shared infrastructure singletons (Supabase + React Query) + auth hook stub

**Files:**
- Create: `frontend/src/lib/supabase.ts`
- Create: `frontend/src/lib/queryClient.ts`
- Create: `frontend/src/hooks/useAuthSession.ts`

- [ ] **Step 1: Create the Supabase client singleton**

Create `frontend/src/lib/supabase.ts`:

```ts
import { createClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  throw new Error(
    'Missing Supabase env vars. Copy frontend/.env.example to frontend/.env.local and fill in VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.',
  );
}

export const supabase = createClient(url, anonKey);
```

- [ ] **Step 2: Create the React Query client singleton**

Create `frontend/src/lib/queryClient.ts`:

```ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

- [ ] **Step 3: Create the `useAuthSession` hook stub**

Create `frontend/src/hooks/useAuthSession.ts`:

```ts
import type { Session } from '@supabase/supabase-js';

export interface AuthSessionState {
  session: Session | null;
  loading: boolean;
}

/**
 * Stub. Real implementation (subscribes to supabase.auth.onAuthStateChange)
 * lands when the /auth page does. Returns logged-out + not-loading so
 * pages can render without errors during scaffolding.
 */
export function useAuthSession(): AuthSessionState {
  return { session: null, loading: false };
}
```

- [ ] **Step 4: Commit**

Run from repo root:

```bash
git add frontend/src/lib/supabase.ts frontend/src/lib/queryClient.ts frontend/src/hooks/useAuthSession.ts
git commit -m "feat(frontend): add Supabase, QueryClient singletons and auth hook stub"
```

---

## Task 8: API fetch wrapper (TDD)

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/__tests__/client.test.ts`
- Create: `frontend/src/__tests__/setup.ts` (referenced by `vite.config.ts`)

- [ ] **Step 1: Create the Vitest setup file**

Create `frontend/src/__tests__/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 2: Write the failing test**

Create `frontend/src/api/__tests__/client.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch } from '@/api/client';

const mockSession = vi.fn();

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: () => mockSession(),
    },
  },
}));

describe('apiFetch', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    mockSession.mockResolvedValue({ data: { session: null }, error: null });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.clearAllMocks();
  });

  it('returns parsed JSON on 2xx', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const result = await apiFetch<{ ok: boolean }>('/me');
    expect(result).toEqual({ ok: true });
  });

  it('attaches Authorization header when session exists', async () => {
    mockSession.mockResolvedValue({
      data: { session: { access_token: 'tok_abc' } },
      error: null,
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
    globalThis.fetch = fetchMock;

    await apiFetch('/me');

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get('Authorization')).toBe('Bearer tok_abc');
  });

  it('throws ApiError with status, code, message on non-2xx', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: 'not_found', message: 'group not found' } }),
        { status: 404, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    await expect(apiFetch('/groups/xyz')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      code: 'not_found',
      message: 'group not found',
    });
  });

  it('throws ApiError with generic code when body is unparseable', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response('not-json', { status: 500 }),
    );

    const err = await apiFetch('/anything').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(500);
    expect((err as ApiError).code).toBe('unknown');
  });
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run from `frontend/`:

```bash
npm run test
```

Expected: failure — `Cannot find module '@/api/client'` or similar.

- [ ] **Step 4: Implement the API client**

Create `frontend/src/api/client.ts`:

```ts
import { supabase } from '@/lib/supabase';

/**
 * Cache key convention (used with @tanstack/react-query):
 *   ['me']
 *   ['groups', groupId, 'feed']
 *   ['groups', groupId, 'leaderboard', window]
 *   ['groups', groupId, 'messages']
 * Keys are arrays mirroring the URL.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export class ApiError extends Error {
  override name = 'ApiError';
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const headers = new Headers(init.headers);
  if (data.session?.access_token) {
    headers.set('Authorization', `Bearer ${data.session.access_token}`);
  }
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let code = 'unknown';
    let message = res.statusText || 'Request failed';
    try {
      const body = (await res.json()) as { error?: { code?: string; message?: string } };
      if (body.error?.code) code = body.error.code;
      if (body.error?.message) message = body.error.message;
    } catch {
      // body wasn't JSON; keep defaults
    }
    throw new ApiError(res.status, code, message);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run from `frontend/`:

```bash
npm run test
```

Expected: 4 tests passing in `client.test.ts`.

- [ ] **Step 6: Commit**

Run from repo root:

```bash
git add frontend/src/api/client.ts frontend/src/api/__tests__/client.test.ts frontend/src/__tests__/setup.ts
git commit -m "feat(frontend): add apiFetch wrapper with ApiError, JWT attach"
```

---

## Task 9: Stub pages (7 routes) + components dir placeholder

**Files:**
- Create: `frontend/src/pages/Home.tsx`
- Create: `frontend/src/pages/Auth.tsx`
- Create: `frontend/src/pages/Crews.tsx`
- Create: `frontend/src/pages/CrewDetail.tsx`
- Create: `frontend/src/pages/PostSleep.tsx`
- Create: `frontend/src/pages/UserProfile.tsx`
- Create: `frontend/src/pages/Settings.tsx`
- Create: `frontend/src/components/.gitkeep`

Each stub has the same shape: one `<h1>` for the route name plus a small "owned by X" note. The owner note disappears when each teammate replaces their stub.

- [ ] **Step 1: Create `Home.tsx`**

Create `frontend/src/pages/Home.tsx`:

```tsx
export default function Home() {
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">synzoia</h1>
      <p className="text-sm text-gray-500">/ — landing / redirect (TBD)</p>
    </main>
  );
}
```

- [ ] **Step 2: Create `Auth.tsx`**

Create `frontend/src/pages/Auth.tsx`:

```tsx
export default function Auth() {
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Sign in / Sign up</h1>
      <p className="text-sm text-gray-500">/auth — owned by Micah</p>
    </main>
  );
}
```

- [ ] **Step 3: Create `Crews.tsx`**

Create `frontend/src/pages/Crews.tsx`:

```tsx
export default function Crews() {
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">My crews</h1>
      <p className="text-sm text-gray-500">/crews — owned by Micah</p>
    </main>
  );
}
```

- [ ] **Step 4: Create `CrewDetail.tsx`**

Create `frontend/src/pages/CrewDetail.tsx`:

```tsx
import { useParams } from 'react-router-dom';

export default function CrewDetail() {
  const { id } = useParams<{ id: string }>();
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Crew {id}</h1>
      <p className="text-sm text-gray-500">
        /crews/:id — shell + leaderboard tab owned by Micah; feed tab by Teammate A;
        chat tab by Teammate B
      </p>
    </main>
  );
}
```

- [ ] **Step 5: Create `PostSleep.tsx`**

Create `frontend/src/pages/PostSleep.tsx`:

```tsx
import { useParams } from 'react-router-dom';

export default function PostSleep() {
  const { id } = useParams<{ id: string }>();
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Post sleep for crew {id}</h1>
      <p className="text-sm text-gray-500">/crews/:id/post — owned by Teammate A</p>
    </main>
  );
}
```

- [ ] **Step 6: Create `UserProfile.tsx`**

Create `frontend/src/pages/UserProfile.tsx`:

```tsx
import { useParams } from 'react-router-dom';

export default function UserProfile() {
  const { id } = useParams<{ id: string }>();
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">User {id}</h1>
      <p className="text-sm text-gray-500">/users/:id — owned by Teammate A</p>
    </main>
  );
}
```

- [ ] **Step 7: Create `Settings.tsx`**

Create `frontend/src/pages/Settings.tsx`:

```tsx
export default function Settings() {
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <p className="text-sm text-gray-500">/settings — unassigned</p>
    </main>
  );
}
```

- [ ] **Step 8: Create `src/components/.gitkeep`**

Empty placeholder so the `components/` directory exists in git for future reusable UI to live in.

Run from `frontend/`:

```bash
mkdir -p src/components && touch src/components/.gitkeep
```

- [ ] **Step 9: Commit**

Run from repo root:

```bash
git add frontend/src/pages frontend/src/components/.gitkeep
git commit -m "feat(frontend): add 7 route stub pages + components dir"
```

---

## Task 10: App routes + smoke test (TDD)

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/__tests__/smoke.test.tsx`

- [ ] **Step 1: Write the failing smoke test**

Create `frontend/src/__tests__/smoke.test.tsx`:

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
    '/',
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
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `frontend/`:

```bash
npm run test
```

Expected: failure — `Cannot find module '@/App'`.

- [ ] **Step 3: Implement `App.tsx`**

Create `frontend/src/App.tsx`:

```tsx
import { Route, Routes } from 'react-router-dom';
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
      <Route path="/crews" element={<Crews />} />
      <Route path="/crews/:id" element={<CrewDetail />} />
      <Route path="/crews/:id/post" element={<PostSleep />} />
      <Route path="/users/:id" element={<UserProfile />} />
      <Route path="/settings" element={<Settings />} />
    </Routes>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run from `frontend/`:

```bash
npm run test
```

Expected: 4 `client.test.ts` tests + 7 smoke tests = **11 passing**.

- [ ] **Step 5: Commit**

Run from repo root:

```bash
git add frontend/src/App.tsx frontend/src/__tests__/smoke.test.tsx
git commit -m "feat(frontend): add App routes shell + smoke test"
```

---

## Task 11: Entry point `main.tsx`

**Files:**
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Create `main.tsx`**

Create `frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
import App from '@/App';
import '@/index.css';

const rootEl = document.getElementById('root');
if (!rootEl) {
  throw new Error('No #root element found in index.html');
}

createRoot(rootEl).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 2: Commit**

Run from repo root:

```bash
git add frontend/src/main.tsx
git commit -m "feat(frontend): add main.tsx entry with providers"
```

---

## Task 12: `.env.example`

**Files:**
- Create: `frontend/.env.example`

- [ ] **Step 1: Create the env example**

Create `frontend/.env.example`:

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
```

- [ ] **Step 2: Commit**

Run from repo root:

```bash
git add frontend/.env.example
git commit -m "feat(frontend): document env vars in .env.example"
```

---

## Task 13: Run the spec's acceptance checks end-to-end

**Files:** none modified. This task verifies the scaffold against §9 of the spec.

- [ ] **Step 1: Fresh install resolves cleanly**

Run from `frontend/`:

```bash
rm -rf node_modules
npm ci
```

Expected: exits 0; `node_modules/` recreated from the committed lockfile.

- [ ] **Step 2: Typecheck passes**

Run from `frontend/`:

```bash
npm run typecheck
```

Expected: exits 0, no output.

- [ ] **Step 3: Lint passes**

Run from `frontend/`:

```bash
npm run lint
```

Expected: exits 0, no errors. Warnings tolerated.

- [ ] **Step 4: Tests pass**

Run from `frontend/`:

```bash
npm run test
```

Expected: 11 tests pass (4 in `client.test.ts`, 7 in `smoke.test.tsx`).

- [ ] **Step 5: Production build succeeds**

Run from `frontend/`:

```bash
npm run build
```

Expected: exits 0; `dist/` directory created containing `index.html` and an `assets/` folder.

- [ ] **Step 6: Dev server renders every route (manual)**

Create `frontend/.env.local` with placeholder values (real Supabase project not required for this check — the browser will throw at first auth call, but the stub pages don't trigger that):

```
VITE_SUPABASE_URL=https://placeholder.supabase.co
VITE_SUPABASE_ANON_KEY=placeholder-anon-key
VITE_API_BASE_URL=http://localhost:8000
```

Run from `frontend/`:

```bash
npm run dev
```

In the browser, visit each route in turn and confirm the corresponding `<h1>` appears:

- `http://localhost:5173/` → "synzoia"
- `http://localhost:5173/auth` → "Sign in / Sign up"
- `http://localhost:5173/crews` → "My crews"
- `http://localhost:5173/crews/abc` → "Crew abc"
- `http://localhost:5173/crews/abc/post` → "Post sleep for crew abc"
- `http://localhost:5173/users/xyz` → "User xyz"
- `http://localhost:5173/settings` → "Settings"

Stop the dev server (Ctrl-C). Delete `frontend/.env.local` (it's gitignored, but keep the dir clean).

- [ ] **Step 7: Missing env vars produce a clear error (manual)**

This is spec §9 check #7. With no `.env.local` present, the Supabase module throws on import.

Run from `frontend/`:

```bash
npm run dev
```

Visit `http://localhost:5173/` and open the browser console. Expected: error containing `Missing Supabase env vars. Copy frontend/.env.example to frontend/.env.local...`.

Stop the dev server.

- [ ] **Step 8: Final commit (if any cleanup made it in)**

Run from repo root:

```bash
git status
```

Expected: clean working tree. If anything is uncommitted from steps above (it shouldn't be), commit it now with a descriptive message.

---

## Scaffold complete

After Task 13 passes, all three teammates can:

1. `git pull`
2. `cd frontend && npm install`
3. `cp .env.example .env.local` and fill in real Supabase values
4. `npm run dev`
5. Open the page they own and start replacing the stub with real UI

The next implementation plan (separate document, not this one) will be for whichever page or feature comes next — most likely either the auth flow + `useAuthSession` real implementation, or the visual identity / theme tokens. That decision is for Micah and Teammate B to make after this scaffold lands.
