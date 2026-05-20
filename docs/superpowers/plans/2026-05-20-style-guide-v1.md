# synzoia v1 style guide — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install shadcn/ui, apply the ocean-breeze theme from tweakcn, migrate primitives onto shadcn base components, wire system-default dark mode, ship a `/style-guide` reference route, and restyle every page + layout chrome with semantic tokens.

**Architecture:** shadcn/ui + Radix primitives in `src/components/ui/` (lowercase shadcn files) with thin PascalCase wrapper files preserving existing callsite APIs. Ocean-breeze CSS variables in `src/index.css` drive every color; semantic class tokens (`bg-card`, `text-foreground`, `bg-primary`, …) replace hardcoded slate/indigo. Dark mode uses `@media (prefers-color-scheme: dark)` so OS preference flips the theme without JS.

**Tech Stack:** React 19, Vite 8, Tailwind CSS v4, TypeScript 6, shadcn/ui (Tailwind v4 mode), Radix UI, React Router 7, Vitest.

**Spec:** [`docs/superpowers/specs/2026-05-20-style-guide-v1-design.md`](../specs/2026-05-20-style-guide-v1-design.md)

**Conventions for every task below:**
- All commands assume CWD is `frontend/` unless otherwise noted.
- "Run smoke tests" means `npm run test` — should always show 11 passing tests (12 after Task 11).
- After every commit, run `npm run typecheck && npm run lint && npm run test`. Don't move on if any fail.

---

## Task 1: shadcn init + path aliases

**Files:**
- Create: `frontend/components.json`
- Create: `frontend/src/lib/utils.ts`
- Modify: `frontend/tsconfig.app.json`
- Modify: `frontend/tsconfig.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/package.json` (deps added by shadcn)
- Modify: `frontend/src/index.css` (shadcn will rewrite this — we re-apply our customizations after Task 2)

- [ ] **Step 1: Confirm CWD is `frontend/`**

```bash
pwd
```

Expected: ends with `/synzoia/frontend`.

- [ ] **Step 2: Run shadcn init**

```bash
npx shadcn@latest init
```

When prompted, answer:
- Which style? → **New York**
- Which color? → **Neutral** (the ocean-breeze theme overrides this in Task 2)
- TypeScript? → **yes**
- Use CSS variables? → **yes**
- Tailwind config? → **(should auto-detect v4)**
- React Server Components? → **no**
- Configure path aliases? → **yes** (defaults `@/*` → `./src/*`)
- Write to `src/lib/utils.ts`? → **yes**

This installs `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `tw-animate-css` and rewrites `src/index.css`.

- [ ] **Step 3: Verify path alias landed in tsconfig**

```bash
grep -A2 '"paths"' tsconfig.app.json
```

Expected:
```
"paths": {
  "@/*": ["./src/*"]
}
```

If missing, add to `compilerOptions`:
```json
"baseUrl": ".",
"paths": { "@/*": ["./src/*"] }
```

Also ensure `tsconfig.json` has the same `paths` in `compilerOptions` if shadcn didn't add it (some setups need both).

- [ ] **Step 4: Add the path alias to vite.config.ts**

Open `frontend/vite.config.ts`. It currently looks roughly like:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
```

Add `path` import and a `resolve.alias` block:

```ts
import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

- [ ] **Step 5: Verify shadcn created utils.ts**

```bash
cat src/lib/utils.ts
```

Expected: a file exporting a `cn` function that wraps `clsx` + `twMerge`.

- [ ] **Step 6: Run typecheck + smoke tests**

```bash
npm run typecheck && npm run test
```

Expected: both exit 0. The smoke tests should still pass (we haven't touched any pages yet).

If typecheck fails on missing `@/*` resolution, double-check Step 3.

- [ ] **Step 7: Commit**

```bash
git add frontend/components.json frontend/src/lib/utils.ts frontend/tsconfig.app.json frontend/tsconfig.json frontend/vite.config.ts frontend/package.json frontend/package-lock.json frontend/src/index.css
git commit -m "chore(frontend): init shadcn/ui with path aliases"
```

---

## Task 2: Apply ocean-breeze theme + system-default dark mode

**Files:**
- Modify: `frontend/src/index.css` (shadcn add will rewrite the variable blocks; we then edit dark-mode wiring)

- [ ] **Step 1: Apply ocean-breeze theme**

```bash
npx shadcn@latest add https://tweakcn.com/r/themes/ocean-breeze.json
```

This rewrites `src/index.css` with two CSS-variable blocks: one in `:root` (light), one in `.dark` (dark). It also sets `--radius` and font tokens.

- [ ] **Step 2: Read the current index.css**

```bash
cat src/index.css
```

You should see something like (structure — exact values come from ocean-breeze):

```css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

:root {
  --background: oklch(...);
  --foreground: oklch(...);
  /* ... many more ... */
  --radius: 0.5rem;
}

.dark {
  --background: oklch(...);
  /* ... etc ... */
}

@theme inline {
  --color-background: var(--background);
  /* ... etc ... */
}

@layer base {
  * { @apply border-border outline-ring/50; }
  body { @apply bg-background text-foreground; }
}
```

- [ ] **Step 3: Convert `.dark` block to media-query**

Replace the `.dark { ... }` selector block with a media query that applies the same variables to `:root` when OS is dark. Keep everything else.

Find this:
```css
.dark {
  --background: oklch(...);
  /* ...all the dark vars... */
}
```

Replace with:
```css
@media (prefers-color-scheme: dark) {
  :root {
    --background: oklch(...);
    /* ...the same dark vars... */
  }
}
```

Also remove the `@custom-variant dark (&:is(.dark *));` line — we no longer need it because we're not using the `.dark` class anywhere. (If you keep the variant, that's also fine; it just becomes inert. Removing is cleaner.)

- [ ] **Step 4: Re-add the body font stack our shallow design used**

The shallow-pass `body` rule had an explicit Inter + system stack. Ocean-breeze may have set `--font-sans` to something — keep that, but if our body lacks a `font-family`, add it back inside `@layer base`:

```css
@layer base {
  * { @apply border-border outline-ring/50; }
  html, body, #root { height: 100%; }
  body {
    @apply bg-background text-foreground antialiased;
    font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", system-ui, sans-serif);
  }
}
```

- [ ] **Step 5: Run dev server and visually verify**

```bash
npm run dev
```

Open http://localhost:5173/auth. You should see ocean-breeze's light background — not pure white, not the old warm off-white. The exact color comes from the theme; eyeball that it's clearly different.

Then toggle your OS appearance to Dark (macOS: System Settings → Appearance → Dark). The page should flip to a dark ocean-breeze palette without reload. Toggle back to Light to confirm round-trip.

Kill the dev server (Ctrl+C).

- [ ] **Step 6: Run typecheck + tests**

```bash
npm run typecheck && npm run test
```

Expected: both exit 0.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(frontend): apply ocean-breeze theme with system dark mode"
```

---

## Task 3: Install shadcn base primitives

**Files:**
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/card.tsx`
- Create: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/label.tsx`
- Create: `frontend/src/components/ui/tabs.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/ui/avatar.tsx`
- Create: `frontend/src/components/ui/separator.tsx`
- Modify: `frontend/package.json` (Radix deps)

**Heads up — file naming collision:** Our existing wrappers are PascalCase (`Button.tsx`, `Card.tsx`, etc.). shadcn writes lowercase (`button.tsx`, `card.tsx`, etc.). On case-insensitive macOS this would conflict if they were in the same dir tree on a case-sensitive FS. To be safe, our wrappers stay PascalCase and import from `@/components/ui/button` (the shadcn one). Git treats them as different paths on case-sensitive systems, but case-insensitive macOS may collapse them. Verify after install with `ls src/components/ui` — you should see BOTH `Button.tsx` and `button.tsx` listed. If you see only one, the FS collapsed them and you need to rename the wrappers in subsequent tasks (e.g., `AppButton.tsx`).

- [ ] **Step 1: Install all eight primitives**

```bash
npx shadcn@latest add button card input label tabs badge avatar separator
```

When prompted about overwriting any existing file: **no, do not overwrite our PascalCase files**. shadcn should write only lowercase files.

- [ ] **Step 2: Verify both case variants exist**

```bash
ls -la src/components/ui
```

You should see all eight new lowercase files (`button.tsx`, `card.tsx`, `input.tsx`, `label.tsx`, `tabs.tsx`, `badge.tsx`, `avatar.tsx`, `separator.tsx`) AND the original PascalCase wrappers (`Button.tsx`, `Card.tsx`, `EmptyState.tsx`, `FormField.tsx`, `PageHeader.tsx`, `TabStrip.tsx`).

If you only see lowercase versions of `Button.tsx`/`Card.tsx` (case collapse on macOS), STOP. Rename the PascalCase wrappers to `AppButton.tsx`/`AppCard.tsx` in the upcoming tasks and update all imports accordingly. The rest of this plan assumes PascalCase wrappers stayed intact.

- [ ] **Step 3: Run typecheck + tests**

```bash
npm run typecheck && npm run test
```

Expected: both exit 0. (Nothing imports the new shadcn files yet, so no behavior changes.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): install shadcn primitives (button card input label tabs badge avatar separator)"
```

---

## Task 4: Migrate Button wrapper

**Files:**
- Modify: `frontend/src/components/ui/Button.tsx`
- Reference: `frontend/src/components/ui/__tests__/` (any existing Button test)

- [ ] **Step 1: Read the current Button.tsx**

```bash
cat src/components/ui/Button.tsx
```

Note the existing prop signature so the rewrite preserves it.

- [ ] **Step 2: Read existing button tests**

```bash
ls src/components/ui/__tests__/
```

Skim any `Button.test.tsx`. The rewritten wrapper must keep all asserted behavior (variants, disabled, `to` prop renders Link).

- [ ] **Step 3: Rewrite Button.tsx as a thin wrapper**

Replace `src/components/ui/Button.tsx` with:

```tsx
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { Button as ShadcnButton } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type Variant = 'primary' | 'secondary' | 'ghost';

const variantMap = {
  primary: 'default',
  secondary: 'outline',
  ghost: 'ghost',
} as const;

type CommonProps = {
  variant?: Variant;
  className?: string;
  children: ReactNode;
  disabled?: boolean;
};

type ButtonAsButton = CommonProps & {
  to?: undefined;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
};

type ButtonAsLink = CommonProps & {
  to: string;
  onClick?: undefined;
  type?: undefined;
};

type Props = ButtonAsButton | ButtonAsLink;

export function Button(props: Props) {
  const { variant = 'primary', className, children, disabled } = props;
  const shadcnVariant = variantMap[variant];

  if ('to' in props && props.to) {
    if (disabled) {
      return (
        <ShadcnButton variant={shadcnVariant} disabled className={cn(className)}>
          {children}
        </ShadcnButton>
      );
    }
    return (
      <ShadcnButton asChild variant={shadcnVariant} className={cn(className)}>
        <Link to={props.to}>{children}</Link>
      </ShadcnButton>
    );
  }

  return (
    <ShadcnButton
      variant={shadcnVariant}
      disabled={disabled}
      onClick={props.onClick}
      type={props.type ?? 'button'}
      className={cn(className)}
    >
      {children}
    </ShadcnButton>
  );
}
```

- [ ] **Step 4: Run smoke tests**

```bash
npm run test
```

Expected: all 11 tests still pass. If a Button-specific test asserts an exact class string (`bg-indigo-600`), that test needs updating — but the smoke tests don't check classes, so most likely you're fine.

If a test does fail on class assertions, update the test to assert role/text instead of classes (e.g., `getByRole('button', { name: 'Sign in' })`).

- [ ] **Step 5: Run typecheck**

```bash
npm run typecheck
```

Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ui/Button.tsx
git commit -m "refactor(frontend): wrap shadcn Button preserving primary/secondary/ghost + to= API"
```

---

## Task 5: Migrate Card wrapper

**Files:**
- Modify: `frontend/src/components/ui/Card.tsx`

- [ ] **Step 1: Read the current Card.tsx**

```bash
cat src/components/ui/Card.tsx
```

Note the prop signature (should be `{ className?, children }`).

- [ ] **Step 2: Rewrite Card.tsx as a thin wrapper**

Replace `src/components/ui/Card.tsx` with:

```tsx
import type { ReactNode } from 'react';
import { Card as ShadcnCard, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

type Props = {
  className?: string;
  children: ReactNode;
};

export function Card({ className, children }: Props) {
  return (
    <ShadcnCard className={cn(className)}>
      <CardContent className="p-6">{children}</CardContent>
    </ShadcnCard>
  );
}
```

Note: shadcn `Card` has separate `CardHeader`/`CardContent`/`CardFooter` slots. For our existing one-slot use case we keep the simple wrapper. If a future page needs structured cards, callers can import `ShadcnCard` directly from `@/components/ui/card`.

- [ ] **Step 3: Run smoke tests + typecheck**

```bash
npm run typecheck && npm run test
```

Expected: both exit 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/Card.tsx
git commit -m "refactor(frontend): wrap shadcn Card preserving simple one-slot API"
```

---

## Task 6: Migrate FormField wrapper

**Files:**
- Modify: `frontend/src/components/ui/FormField.tsx`

- [ ] **Step 1: Read the current FormField.tsx**

```bash
cat src/components/ui/FormField.tsx
```

Note the prop signature.

- [ ] **Step 2: Rewrite FormField.tsx using shadcn Label + Input**

Replace `src/components/ui/FormField.tsx` with:

```tsx
import type { InputHTMLAttributes } from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  id: string;
  error?: string;
};

export function FormField({ label, id, error, className, ...inputProps }: Props) {
  return (
    <div className={cn('space-y-2', className)}>
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} aria-invalid={!!error || undefined} {...inputProps} />
      {error && (
        <p className="text-destructive text-sm" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Run smoke tests + typecheck**

```bash
npm run typecheck && npm run test
```

Expected: both exit 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/FormField.tsx
git commit -m "refactor(frontend): rebuild FormField on shadcn Label + Input"
```

---

## Task 7: Restyle PageHeader + EmptyState

**Files:**
- Modify: `frontend/src/components/ui/PageHeader.tsx`
- Modify: `frontend/src/components/ui/EmptyState.tsx`

- [ ] **Step 1: Read both current files**

```bash
cat src/components/ui/PageHeader.tsx src/components/ui/EmptyState.tsx
```

- [ ] **Step 2: Rewrite PageHeader.tsx with semantic tokens**

Replace `src/components/ui/PageHeader.tsx` with:

```tsx
import type { ReactNode } from 'react';

type Props = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export function PageHeader({ title, description, action }: Props) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description && (
          <p className="text-muted-foreground text-sm mt-1">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
```

- [ ] **Step 3: Rewrite EmptyState.tsx with semantic tokens**

Replace `src/components/ui/EmptyState.tsx` with:

```tsx
type Props = {
  message?: string;
};

export function EmptyState({ message = 'Coming soon' }: Props) {
  return (
    <div className="py-12 text-center text-muted-foreground text-sm">
      {message}
    </div>
  );
}
```

- [ ] **Step 4: Run smoke tests + typecheck**

```bash
npm run typecheck && npm run test
```

Expected: both exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/PageHeader.tsx frontend/src/components/ui/EmptyState.tsx
git commit -m "refactor(frontend): restyle PageHeader + EmptyState with semantic tokens"
```

---

## Task 8: Migrate TabStrip on shadcn Tabs

**Files:**
- Modify: `frontend/src/components/ui/TabStrip.tsx`

The tricky part: shadcn `Tabs` is a controlled component pair (`Tabs` + `TabsList` + `TabsTrigger` + `TabsContent`). Our `TabStrip` only renders the tab bar — caller decides what to render below. So we use `Tabs` + `TabsList` + `TabsTrigger` only, controlled by the URL search param.

- [ ] **Step 1: Read the current TabStrip.tsx**

```bash
cat src/components/ui/TabStrip.tsx
```

Confirm: it reads `?tab=` via `useSearchParams`, writes back on click, and renders just the bar (no content slot).

- [ ] **Step 2: Rewrite TabStrip.tsx on shadcn Tabs**

Replace `src/components/ui/TabStrip.tsx` with:

```tsx
import { useSearchParams } from 'react-router-dom';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

type Tab = { key: string; label: string };

type Props = {
  tabs: Tab[];
  paramName?: string;
  defaultKey?: string;
};

export function TabStrip({ tabs, paramName = 'tab', defaultKey }: Props) {
  const [params, setParams] = useSearchParams();
  const active = params.get(paramName) ?? defaultKey ?? tabs[0]?.key;

  function setActive(key: string) {
    const next = new URLSearchParams(params);
    next.set(paramName, key);
    setParams(next, { replace: true });
  }

  return (
    <Tabs value={active} onValueChange={setActive}>
      <TabsList>
        {tabs.map((t) => (
          <TabsTrigger key={t.key} value={t.key}>
            {t.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
```

- [ ] **Step 3: Run smoke tests + typecheck**

```bash
npm run typecheck && npm run test
```

Expected: both exit 0.

- [ ] **Step 4: Manual verification**

```bash
npm run dev
```

Open http://localhost:5173/crews/abc. Click each tab. Verify:
1. The URL updates to `?tab=feed`, `?tab=leaderboard`, `?tab=chat`.
2. The empty-state message below the tabs swaps (this is the existing page logic reading `params.get('tab')`).
3. Browser back/forward respects tab history? It shouldn't — we used `{ replace: true }`. Clicking back from `?tab=chat` should leave the page, not return to `?tab=feed`. That's the intended behavior to match the prior version.

Kill the dev server.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/TabStrip.tsx
git commit -m "refactor(frontend): rebuild TabStrip on shadcn Tabs primitive"
```

---

## Task 9: Restyle AppLayout + add data-logo-slot

**Files:**
- Modify: `frontend/src/components/layout/AppLayout.tsx`

- [ ] **Step 1: Read the current AppLayout.tsx**

```bash
cat src/components/layout/AppLayout.tsx
```

- [ ] **Step 2: Rewrite AppLayout.tsx with semantic tokens**

Replace `src/components/layout/AppLayout.tsx` with:

```tsx
import { Link, NavLink, Outlet } from 'react-router-dom';

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="bg-background border-b border-border sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/crews" className="flex items-center gap-2">
            <span
              data-logo-slot
              className="text-lg font-semibold tracking-tight text-foreground"
            >
              synzoia
            </span>
          </Link>
          <Link
            to="/settings"
            className="hidden sm:inline text-sm text-muted-foreground hover:text-foreground"
          >
            Settings
          </Link>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 sm:px-6 py-6 pb-24 sm:pb-6">
        <Outlet />
      </main>

      <nav
        className="sm:hidden fixed bottom-0 inset-x-0 bg-card border-t border-border"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="flex">
          <NavLink
            to="/crews"
            className={({ isActive }) =>
              `flex-1 py-3 text-center text-sm font-medium ${
                isActive ? 'text-primary' : 'text-muted-foreground'
              }`
            }
          >
            Crews
          </NavLink>
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex-1 py-3 text-center text-sm font-medium ${
                isActive ? 'text-primary' : 'text-muted-foreground'
              }`
            }
          >
            Settings
          </NavLink>
        </div>
      </nav>
    </div>
  );
}
```

- [ ] **Step 3: Run smoke tests + typecheck**

```bash
npm run typecheck && npm run test
```

Expected: both exit 0.

- [ ] **Step 4: Manual verification**

```bash
npm run dev
```

Open http://localhost:5173/crews. Verify:
1. Top bar has ocean-breeze background, "synzoia" wordmark on left, "Settings" on right (desktop).
2. Resize to mobile (Chrome devtools → 375px). Settings link disappears from top, bottom tab bar appears with Crews + Settings.
3. Active route gets the primary color treatment in the bottom bar.

Kill the dev server.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/AppLayout.tsx
git commit -m "refactor(frontend): restyle AppLayout with semantic tokens + data-logo-slot"
```

---

## Task 10: Restyle all 7 pages with semantic tokens

This is the mechanical pass. Each page gets the same find-and-replace.

**Files:**
- Modify: `frontend/src/pages/Auth.tsx`
- Modify: `frontend/src/pages/Crews.tsx`
- Modify: `frontend/src/pages/CrewDetail.tsx`
- Modify: `frontend/src/pages/PostSleep.tsx`
- Modify: `frontend/src/pages/UserProfile.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- (Home.tsx is a pure redirect — no styling.)

**Token swap table (apply to every page):**

| Find | Replace |
|---|---|
| `bg-white` | `bg-card` |
| `text-slate-900` | `text-foreground` |
| `text-slate-500` | `text-muted-foreground` |
| `text-slate-600` | `text-muted-foreground` |
| `bg-indigo-600` | `bg-primary` |
| `hover:bg-indigo-700` | `hover:bg-primary/90` |
| `text-indigo-600` | `text-primary` |
| `text-indigo-700` | `text-primary` |
| `border-slate-200` | `border-border` |
| `border-slate-300` | `border-border` |
| `hover:bg-slate-50` | `hover:bg-muted` |
| `rounded-2xl` (on card surfaces) | `rounded-xl` |

- [ ] **Step 1: Auth.tsx**

```bash
cat src/pages/Auth.tsx
```

Apply the token swap table to every class string. Also: the centered wrapper `min-h-screen` should sit on `bg-background` so the page surface matches the theme. The wordmark `synzoia` `<h1>` keeps the smoke-test contract.

Save, then:

```bash
npm run typecheck && npm run test
```

Expected: both exit 0.

- [ ] **Step 2: Crews.tsx**

```bash
cat src/pages/Crews.tsx
```

Apply token swaps. Save.

- [ ] **Step 3: CrewDetail.tsx**

```bash
cat src/pages/CrewDetail.tsx
```

Apply token swaps. Pay attention to the active-tab indicator if it has hardcoded colors — but if `TabStrip` is now shadcn-based, the page shouldn't be styling tabs directly.

Save.

- [ ] **Step 4: PostSleep.tsx**

```bash
cat src/pages/PostSleep.tsx
```

Apply token swaps. Save.

- [ ] **Step 5: UserProfile.tsx**

```bash
cat src/pages/UserProfile.tsx
```

Apply token swaps. Save.

- [ ] **Step 6: Settings.tsx**

```bash
cat src/pages/Settings.tsx
```

Apply token swaps. Save. Also consider inserting `<Separator className="my-4" />` (import from `@/components/ui/separator`) between the Profile / Sign out / About sections — this is the first real consumer of the shadcn Separator and improves the visual rhythm.

- [ ] **Step 7: Grep for leftover hardcoded color classes**

```bash
grep -RnE '(bg-white|bg-indigo-|text-slate-|text-indigo-|border-slate-|hover:bg-slate-|hover:bg-indigo-)' src/pages src/components/layout
```

Expected: zero results. If anything appears, fix it before continuing.

- [ ] **Step 8: Run typecheck + tests**

```bash
npm run typecheck && npm run test
```

Expected: both exit 0.

- [ ] **Step 9: Manual verification of all 7 routes**

```bash
npm run dev
```

Visit each: `/auth`, `/crews`, `/crews/abc`, `/crews/abc/post`, `/users/xyz`, `/settings`. Verify:
1. No leftover indigo/slate colors anywhere — everything reads as ocean-breeze.
2. Card surfaces use `bg-card`, not pure white.
3. Disabled buttons still look disabled (opacity + cursor).
4. The `synzoia` wordmark on `/auth` is still an `<h1>` (smoke test depends on it).

Toggle OS dark mode and re-spot-check at least `/auth` and `/crews/abc`. Both palettes should look intentional.

Kill the dev server.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pages
git commit -m "refactor(frontend): restyle all pages with ocean-breeze semantic tokens"
```

---

## Task 11: Build StyleGuide page + add route + smoke test

**Files:**
- Create: `frontend/src/pages/StyleGuide.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/__tests__/smoke.test.tsx`

- [ ] **Step 1: Write the failing smoke test for /style-guide**

Open `src/__tests__/smoke.test.tsx`. Find the `routesWithHeading` array (or wherever route h1 assertions live). Add `/style-guide` to it.

If the test file currently looks like:

```tsx
const routesWithHeading = [
  '/auth',
  '/crews',
  '/crews/abc',
  '/crews/abc/post',
  '/users/xyz',
  '/settings',
];
```

Change it to:

```tsx
const routesWithHeading = [
  '/auth',
  '/crews',
  '/crews/abc',
  '/crews/abc/post',
  '/users/xyz',
  '/settings',
  '/style-guide',
];
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
npm run test
```

Expected: 11 tests pass, 1 fails — the new `renders an <h1> at /style-guide` test (no route defined yet, no h1 rendered).

- [ ] **Step 3: Create the StyleGuide page**

Create `src/pages/StyleGuide.tsx`:

```tsx
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FormField } from '@/components/ui/FormField';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { TabStrip } from '@/components/ui/TabStrip';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';

const tokens = [
  'background',
  'foreground',
  'card',
  'card-foreground',
  'popover',
  'popover-foreground',
  'primary',
  'primary-foreground',
  'secondary',
  'secondary-foreground',
  'muted',
  'muted-foreground',
  'accent',
  'accent-foreground',
  'destructive',
  'destructive-foreground',
  'border',
  'input',
  'ring',
];

function ColorSwatch({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="w-10 h-10 rounded-md border border-border"
        style={{ backgroundColor: `var(--${name})` }}
      />
      <code className="text-xs text-muted-foreground">--{name}</code>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      <Separator />
      <div>{children}</div>
    </section>
  );
}

export function StyleGuide() {
  const [demoTab, setDemoTab] = useState('feed');

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-2xl font-semibold tracking-tight">synzoia style guide</h1>
        <p className="text-muted-foreground text-sm">v1 — ocean-breeze theme</p>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10 space-y-16">
        <Section title="Brand">
          <p className="text-muted-foreground text-sm">
            Wordmark: <span className="text-foreground font-semibold">synzoia</span>.
            Logo asset lands separately; placeholder is the plain text wordmark.
          </p>
        </Section>

        <Section title="Colors">
          <div className="grid grid-cols-2 gap-x-8 gap-y-3">
            <div className="space-y-3">
              <p className="text-sm font-medium">Current OS appearance</p>
              {tokens.map((t) => (
                <ColorSwatch key={t} name={t} />
              ))}
            </div>
            <div className="space-y-3">
              <p className="text-sm font-medium text-muted-foreground">
                (Toggle OS appearance to see the other palette.)
              </p>
            </div>
          </div>
        </Section>

        <Section title="Typography">
          <div className="space-y-3">
            <h1 className="text-4xl font-bold tracking-tight">H1 — Display</h1>
            <h2 className="text-2xl font-semibold tracking-tight">H2 — Section</h2>
            <h3 className="text-lg font-semibold">H3 — Subsection</h3>
            <p className="text-base">Body — default text on background.</p>
            <p className="text-sm text-muted-foreground">Muted — secondary info.</p>
            <p className="text-xs text-muted-foreground">Caption — metadata.</p>
          </div>
        </Section>

        <Section title="Radii">
          <div className="flex gap-4">
            <div className="w-20 h-20 bg-primary rounded-sm" />
            <div className="w-20 h-20 bg-primary rounded-md" />
            <div className="w-20 h-20 bg-primary rounded-lg" />
            <div className="w-20 h-20 bg-primary rounded-xl" />
          </div>
        </Section>

        <Section title="Buttons">
          <div className="flex flex-wrap gap-3">
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="primary" disabled>
              Primary disabled
            </Button>
            <Button variant="secondary" disabled>
              Secondary disabled
            </Button>
            <Button variant="primary" to="/style-guide">
              Primary as link
            </Button>
          </div>
        </Section>

        <Section title="Cards">
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <h3 className="text-lg font-semibold">Simple card</h3>
              <p className="text-muted-foreground text-sm mt-1">
                One-slot card with default padding.
              </p>
            </Card>
            <Card className="bg-muted">
              <h3 className="text-lg font-semibold">Muted card</h3>
              <p className="text-muted-foreground text-sm mt-1">
                Same component, muted surface variant via className.
              </p>
            </Card>
          </div>
        </Section>

        <Section title="Form fields">
          <div className="grid grid-cols-2 gap-4 max-w-xl">
            <FormField id="sg-email" label="Email" type="email" placeholder="you@example.com" />
            <FormField
              id="sg-bad"
              label="With error"
              type="text"
              error="Required"
              defaultValue=""
            />
            <FormField id="sg-disabled" label="Disabled" type="text" disabled />
            <FormField id="sg-number" label="Number" type="number" min={1} max={100} />
          </div>
        </Section>

        <Section title="Tabs">
          <TabStrip
            paramName="sgtab"
            defaultKey="feed"
            tabs={[
              { key: 'feed', label: 'Feed' },
              { key: 'leaderboard', label: 'Leaderboard' },
              { key: 'chat', label: 'Chat' },
            ]}
          />
        </Section>

        <Section title="Empty states">
          <Card>
            <EmptyState />
          </Card>
          <div className="h-4" />
          <Card>
            <EmptyState message="Custom message — feed empty for this crew." />
          </Card>
        </Section>

        <Section title="Badges">
          <div className="flex gap-2">
            <Badge>Default</Badge>
            <Badge variant="secondary">Secondary</Badge>
            <Badge variant="destructive">Destructive</Badge>
            <Badge variant="outline">Outline</Badge>
          </div>
        </Section>

        <Section title="Avatars">
          <div className="flex gap-3">
            <Avatar>
              <AvatarImage src="https://placeholder.com/40" alt="" />
              <AvatarFallback>MB</AvatarFallback>
            </Avatar>
            <Avatar>
              <AvatarFallback>AB</AvatarFallback>
            </Avatar>
            <Avatar>
              <AvatarFallback>CD</AvatarFallback>
            </Avatar>
          </div>
        </Section>

        <Section title="Page header (in context)">
          <PageHeader
            title="Example page"
            description="This is what PageHeader renders inline."
            action={<Button variant="primary">Action</Button>}
          />
        </Section>
      </main>
    </div>
  );
}
```

Note: the unused `useState`/`setDemoTab` symbols — remove them if your eslint config rejects unused vars. The `useState` example is there for if you want to swap TabStrip for a controlled demo later.

Quick cleanup: drop these two lines from the top of the file:

```tsx
import { useState } from 'react';
```

```tsx
const [demoTab, setDemoTab] = useState('feed');
```

- [ ] **Step 4: Add the route in App.tsx**

Open `src/App.tsx`. Find where `/auth` is defined (outside `<AppLayout>`). Add the StyleGuide import and route alongside it.

Add to imports:
```tsx
import { StyleGuide } from './pages/StyleGuide';
```

Add to routes (outside `<Route element={<AppLayout />}>`, alongside `/auth` and `/`):
```tsx
<Route path="/style-guide" element={<StyleGuide />} />
```

- [ ] **Step 5: Run the smoke test to verify it now passes**

```bash
npm run test
```

Expected: 12 tests pass.

- [ ] **Step 6: Run typecheck**

```bash
npm run typecheck
```

Expected: exit 0. If you get unused-variable errors, remove the `useState` import and the unused `demoTab` line from `StyleGuide.tsx`.

- [ ] **Step 7: Manual verification**

```bash
npm run dev
```

Open http://localhost:5173/style-guide. Scroll through every section:
1. Brand — wordmark visible
2. Colors — swatches rendered, names readable
3. Typography — sizes look hierarchical
4. Radii — four progressively rounder squares
5. Buttons — every variant + state visible
6. Cards — simple + muted
7. Form fields — all four states
8. Tabs — clicking tabs updates `?sgtab=` in URL
9. Empty states — default + custom
10. Badges — four variants
11. Avatars — image + fallbacks
12. Page header — title + description + action

Toggle OS dark mode. Every section flips. Spot-check that all swatches actually change color (they should — they read CSS variables).

Kill the dev server.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/StyleGuide.tsx frontend/src/App.tsx frontend/src/__tests__/smoke.test.tsx
git commit -m "feat(frontend): add /style-guide reference route covering all primitives"
```

---

## Task 12: Final acceptance audit

**Files:** none modified — verification only.

- [ ] **Step 1: Grep audit for leftover hardcoded colors**

```bash
grep -RnE '(bg-white|bg-indigo-|text-slate-|text-indigo-|border-slate-|hover:bg-slate-|hover:bg-indigo-)' frontend/src/pages frontend/src/components/layout frontend/src/components/ui/Button.tsx frontend/src/components/ui/Card.tsx frontend/src/components/ui/FormField.tsx frontend/src/components/ui/PageHeader.tsx frontend/src/components/ui/EmptyState.tsx frontend/src/components/ui/TabStrip.tsx
```

Expected: zero results. (Don't grep the shadcn lowercase files — they're allowed to have their own internal class strings.)

- [ ] **Step 2: Confirm data-logo-slot is present**

```bash
grep -n 'data-logo-slot' frontend/src/components/layout/AppLayout.tsx
```

Expected: one match on the wordmark span.

- [ ] **Step 3: Confirm dark mode wiring**

```bash
grep -A2 'prefers-color-scheme: dark' frontend/src/index.css
```

Expected: matches a `@media (prefers-color-scheme: dark)` block that scopes `:root` overrides.

```bash
grep -c '\.dark {' frontend/src/index.css
```

Expected: `0` (we removed the class-based block).

- [ ] **Step 4: Run the full quality gate**

```bash
cd frontend && npm run typecheck && npm run lint && npm run test && npm run build
```

Expected: all exit 0. The build should produce `dist/`.

- [ ] **Step 5: Manual end-to-end check**

```bash
npm run dev
```

Walk through every route in both OS appearances:
- Light: `/`, `/auth`, `/crews`, `/crews/abc`, `/crews/abc?tab=leaderboard`, `/crews/abc?tab=chat`, `/crews/abc/post`, `/users/xyz`, `/settings`, `/style-guide`
- Dark (toggle OS): same set

Confirm:
1. Every page renders in ocean-breeze (no leftover indigo).
2. Both modes look intentional — no contrast issues, no white-on-white.
3. Mobile widths (Chrome devtools, 375px) still show top bar + bottom tab bar correctly.
4. Disabled buttons still look disabled.
5. The wordmark on `/auth` is in an `<h1>`.
6. Tab clicks on `/crews/abc` still update `?tab=` and swap empty-state messages.
7. `/style-guide` shows every primitive.

Kill the dev server.

- [ ] **Step 6: Final commit (only if anything got tweaked in the audit)**

If you fixed anything in Step 5, commit it:

```bash
git add -A
git commit -m "fix(frontend): style guide v1 audit fixes"
```

Otherwise, skip — no empty commits.

---

## Self-review (engineer is done here; planner did this section)

**Spec coverage:**
- §1 Goal — Task 1+2+3 install shadcn and apply theme. Tasks 4–10 cover primitives + pages. Task 11 covers /style-guide. ✓
- §2 Approach — primitive wrappers preserve APIs (Tasks 4–8). Dark via media query in Task 2 Step 3. ✓
- §3.1 shadcn init — Task 1 Step 2. ✓
- §3.2 Path aliases — Task 1 Steps 3–4. ✓
- §3.3 Deps — Tasks 1 and 3 (shadcn handles installs). ✓
- §3.4 Apply ocean-breeze — Task 2 Step 1. ✓
- §3.5 Media-query dark — Task 2 Step 3. ✓
- §4.1 Install primitives — Task 3. ✓
- §4.2 Wrapper migration — Tasks 4–8 (one per existing wrapper). ✓
- §4.3 New primitives (Badge/Avatar/Separator) — installed in Task 3, used in Task 11 (StyleGuide) and Task 10 Step 6 (Separator in Settings). ✓
- §5 Style guide route — Task 11. ✓
- §6 Page restyle pass — Task 10 (mechanical token swap), Task 9 (AppLayout). ✓
- §7 File structure — matches the file-by-file plan above. ✓
- §8 Testing — Task 11 Step 1 adds the new test; smoke counts: 11 → 12. ✓
- §9 Acceptance checks — Task 12 covers all 7. ✓
- §10 Pushback list — embedded as constraints throughout (no toggle UI, no nav link, no manual variable rewrites). ✓

**Placeholder scan:** No "TBD", "TODO", or vague handwaving. Every code block contains full code. Every command shows expected output.

**Type consistency:** `Variant` type and `variantMap` in Task 4 align with shadcn variant names. `FormField` prop name `error` (Task 6) matches the existing API per the spec. `TabStrip` props (`tabs`, `paramName`, `defaultKey`) consistent between Task 8 implementation and Task 11 usage.

No issues found.
