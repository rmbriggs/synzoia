# synzoia frontend — Scaffolding Design

**Date**: 2026-05-17
**Owner**: Micah (repo-conventions hat, not crews-slice hat)
**Scope**: Stand up `frontend/` so all three teammates can start building their UI slices in parallel.
**Parent spec**: [`2026-05-16-synzoia-design.md`](./2026-05-16-synzoia-design.md)

---

## 1. Goal

Get a Vite + React + TypeScript + Tailwind v4 project standing in `frontend/`, with shared infrastructure (Supabase client, API fetch wrapper, React Query, router shell) wired up and a single passing smoke test. After this lands, any teammate can `git pull && cd frontend && npm install && npm run dev` and immediately edit their assigned page without waiting on anyone else.

**Out of scope**: actual page logic, auth flows, the theme/palette, CI workflow, mobile nav. Each of those is its own follow-up.

## 2. Tooling decisions

| Choice | Picked | Why |
|---|---|---|
| Bundler | Vite 7 | Required by parent spec |
| Framework | React 19 + TypeScript (strict) | Required by parent spec |
| Styling | Tailwind v4 via `@tailwindcss/vite` | Modern default; CSS-first config replaces `tailwind.config.js` |
| Router | `react-router-dom` v7 (declarative) | Current; same shape as v6 |
| Server state | `@tanstack/react-query` v5 | Mandated by `CLAUDE.md` ("React Query for all server data") |
| Supabase | `@supabase/supabase-js` v2 | Auth + realtime per parent spec |
| Tests | Vitest + Testing Library + jsdom | Counts toward spec's "~2 Vitest" target |
| Lint | ESLint flat config + `typescript-eslint` | Required for CI lint step |
| Format | Prettier + `prettier-plugin-tailwindcss` | Class sorting consistency |
| Package manager | npm | Ships with Node; no extra coordination across 3 teammates |
| Path alias | `@/*` → `src/*` | Standard convention; saves `../../..` chains |

## 3. File layout

```
frontend/
├── package.json
├── package-lock.json             # committed
├── tsconfig.json                 # project references root
├── tsconfig.app.json             # app code (strict, jsx, paths)
├── tsconfig.node.json            # vite.config.ts
├── vite.config.ts                # @vitejs/plugin-react, @tailwindcss/vite, @/ alias, vitest config
├── eslint.config.js              # flat config
├── .prettierrc.json
├── index.html
├── .env.example                  # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE_URL
├── .gitignore                    # node_modules, dist, .env, .env.local
├── README.md                     # how to run the dev server
└── src/
    ├── main.tsx                  # mounts App; QueryClientProvider + BrowserRouter
    ├── App.tsx                   # <Routes> shell, 7 routes
    ├── index.css                 # @import "tailwindcss"; + empty @theme {}
    ├── vite-env.d.ts
    ├── lib/
    │   ├── supabase.ts           # singleton SupabaseClient, throws on missing env
    │   └── queryClient.ts        # singleton QueryClient (staleTime 30s)
    ├── api/
    │   └── client.ts             # apiFetch(path, init) — attaches JWT, throws ApiError
    ├── hooks/
    │   └── useAuthSession.ts     # stub returning {session, loading}
    ├── pages/
    │   ├── Home.tsx              # /
    │   ├── Auth.tsx              # /auth                (Micah)
    │   ├── Crews.tsx             # /crews               (Micah)
    │   ├── CrewDetail.tsx        # /crews/:id           (Micah shell + leaderboard tab)
    │   ├── PostSleep.tsx         # /crews/:id/post      (Teammate A)
    │   ├── UserProfile.tsx       # /users/:id           (Teammate A)
    │   └── Settings.tsx          # /settings            (unassigned)
    ├── components/
    │   └── .gitkeep
    └── __tests__/
        └── smoke.test.tsx        # renders <App/> in MemoryRouter, asserts <h1> exists
```

Each stub page renders one `<h1>` with the route name plus an "owned by X" note, so at a glance during week 1 we can see who's responsible for what while the scaffolding is still the only thing visible.

## 4. Dependencies

**runtime**:
`react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `@supabase/supabase-js`

**dev**:
`vite`, `@vitejs/plugin-react`, `typescript`, `@types/react`, `@types/react-dom`, `@types/node`, `tailwindcss`, `@tailwindcss/vite`, `vitest`, `@vitest/ui`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `eslint`, `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `prettier`, `prettier-plugin-tailwindcss`

Versions are whatever `npm install <pkg>` resolves at scaffold time. The resulting `package-lock.json` is committed so all three of us install the same tree.

## 5. npm scripts

| Script | Command | Purpose |
|---|---|---|
| `dev` | `vite` | Local dev server |
| `build` | `tsc -b && vite build` | Production build into `dist/` |
| `preview` | `vite preview` | Serve the built bundle locally |
| `test` | `vitest run` | One-shot test run (CI uses this) |
| `test:watch` | `vitest` | Watch mode during development |
| `lint` | `eslint .` | Required for CI lint step |
| `typecheck` | `tsc -b --noEmit` | Required for CI typecheck step |
| `format` | `prettier --write .` | Manual format pass |

## 6. Shared infrastructure conventions

These conventions are encoded by the scaffold and become load-bearing for every PR after this.

### 6.1 Supabase client singleton

`src/lib/supabase.ts` calls `createClient(url, anonKey)` exactly once at module load. Reads `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` from `import.meta.env`. Throws a clear error at boot if either is missing — fail loud, not at first auth call.

Aligned with `CLAUDE.md` rule: "Single Supabase client instance at `frontend/src/lib/supabase.ts`. Import it; never `new SupabaseClient()` inline."

### 6.2 API fetch wrapper

`src/api/client.ts` exports one function: `apiFetch<T>(path, init?): Promise<T>`. Behavior:

1. Calls `supabase.auth.getSession()` and attaches `Authorization: Bearer <access_token>` if a session exists.
2. Prefixes `path` with `import.meta.env.VITE_API_BASE_URL` (or `/api` in production where FastAPI serves the bundle).
3. On non-2xx, parses the `{error: {code, message}}` body from the spec and throws `class ApiError extends Error { status; code; }`.
4. On 2xx, returns parsed JSON typed as `T`.

Aligned with `CLAUDE.md`: "Errors return `{error: {code, message}}` with the right HTTP status." Components and React Query hooks call `apiFetch`; no raw `fetch` in the codebase.

### 6.3 React Query

`src/lib/queryClient.ts` exports one `QueryClient` instance with `defaultOptions.queries.staleTime = 30_000`. `main.tsx` wraps `<App/>` in `<QueryClientProvider client={queryClient}>`.

Cache-key convention, documented in a comment block at the top of `api/client.ts`: keys are arrays mirroring the URL.

- `['me']`
- `['groups', groupId, 'feed']`
- `['groups', groupId, 'leaderboard', window]`
- `['groups', groupId, 'messages']`

Aligned with `CLAUDE.md`: "Cache keys are stable and match the URL."

### 6.4 Routing

`src/main.tsx` owns the `<BrowserRouter>`. `src/App.tsx` renders just `<Routes>` with the 7 routes from parent spec §7. Splitting it this way means tests can wrap `<App/>` in `<MemoryRouter>` (see §6.6) without nested routers. Each stub renders one `<h1>` plus an owner note. No layout chrome yet — that's a follow-up once we have a visual identity.

### 6.5 Tailwind v4 wiring

`@tailwindcss/vite` plugin in `vite.config.ts`. `src/index.css`:

```css
@import "tailwindcss";

@theme {
  /* Teammate B fills this in (parent spec §10.3) */
}
```

No `tailwind.config.js` — v4 reads theme tokens from the CSS `@theme` block.

### 6.6 Smoke test

`src/__tests__/smoke.test.tsx` renders `<App/>` inside `<MemoryRouter initialEntries={['/']}>` and asserts `document.querySelectorAll('h1').length >= 1`. The point is to prove that the toolchain (Vite + TS + Vitest + jsdom + Testing Library + the QueryClient and router providers) all wire together. Counts toward the parent spec's "~2 Vitest" target; the leaderboard test is the other one, written later by Micah.

## 7. Environment variables

`frontend/.env.example` is committed and lists every var the scaffold reads:

```
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-public-key>
VITE_API_BASE_URL=http://localhost:8000
```

Each teammate copies it to `.env.local` (gitignored) with their own values. In production, FastAPI serves the bundle so `VITE_API_BASE_URL` is `/api`.

Note: the Supabase service role key is **not** in this file — it lives in the backend, never in the frontend bundle.

## 8. What this scaffold does NOT include

Listed explicitly so reviewers don't flag them as omissions:

- **No theme tokens** — `@theme` block is empty, waiting on Teammate B (parent spec §10.3).
- **No CI workflow** — `.github/workflows/ci.yml` is a separate PR.
- **No bottom tab bar / mobile nav chrome** — component work, not scaffolding.
- **No real auth flow** — `Auth.tsx` is a stub. The hook `useAuthSession` returns `{session: null, loading: false}`.
- **No real API calls** — `apiFetch` exists, but no hook calls it yet.
- **No layout component** — every page renders its own `<h1>` for now; layout comes when there's something to lay out.

## 9. Acceptance checks

After scaffolding lands, these all pass:

1. `cd frontend && npm install` completes without error.
2. `npm run dev` starts the dev server; visiting `/`, `/auth`, `/crews`, `/crews/abc`, `/crews/abc/post`, `/users/xyz`, `/settings` each shows the corresponding stub `<h1>`.
3. `npm run build` produces a `dist/` directory.
4. `npm run typecheck` exits 0.
5. `npm run lint` exits 0.
6. `npm run test` runs the smoke test and exits 0.
7. With `.env.local` absent, importing `src/lib/supabase.ts` (e.g. by hitting any page that imports it transitively) throws a clear error about missing env vars.
