# synzoia frontend

React + TypeScript + Vite + Tailwind v4 frontend for synzoia.

## Running locally

````bash
npm install
cp .env.example .env.local      # then fill in your values
npm run dev
````

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
