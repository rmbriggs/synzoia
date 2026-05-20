# synzoia v1 style guide

**Date**: 2026-05-20
**Owner**: Micah (sole frontend + design owner)
**Scope**: Install shadcn/ui, apply the ocean-breeze theme from tweakcn, rebuild existing primitives on shadcn base components, wire system-preference dark mode, ship a `/style-guide` reference route, restyle all 7 pages + `AppLayout`.
**Parent specs**:
- Project design: [`2026-05-16-synzoia-design.md`](./2026-05-16-synzoia-design.md)
- Shallow design pass: [`2026-05-18-frontend-shallow-design-design.md`](./2026-05-18-frontend-shallow-design-design.md)

---

## 1. Goal

The shallow pass (PR #2) explicitly deferred the real style guide. This is that pass. We replace the calm-minimal indigo placeholder with the ocean-breeze theme from tweakcn (a shadcn registry entry), adopt shadcn/ui as the component foundation, and end with a live `/style-guide` page that documents every token and primitive so future work has a stable reference.

**Why now:** branding work is happening tonight in parallel (logo + visual identity). Locking down tokens and primitives unblocks logo placement and keeps the rest of the build consistent as feature waves land.

**Out of scope:**
- Logo asset (placeholder text wordmark stays until logo lands)
- Dark mode toggle UI (system-default only; toggle lands with real Settings)
- Real auth / API wiring (still stubs)
- New pages beyond `/style-guide`
- Animations and micro-interactions
- Icons beyond what shadcn primitives need (`lucide-react` ships with shadcn)

## 2. Approach

shadcn/ui adoption is the foundation. Ocean-breeze is a shadcn registry entry — it expects `components.json`, the `cn` util, CSS variables, and the standard primitive layout. We install all of that, then apply the theme, then migrate our 6 existing primitives one-to-one onto shadcn base components so callsites change as little as possible.

Dark mode uses `@media (prefers-color-scheme: dark)` instead of shadcn's default `.dark` class. No JS, no toggle, follows OS. A toggle is trivial to add later by switching to class-based + a tiny `ThemeProvider`.

## 3. Setup

### 3.1 shadcn init

```
npx shadcn@latest init
```

Answers:
- Style: New York (shadcn default)
- Base color: Neutral (overridden by ocean-breeze immediately after)
- CSS variables: yes
- TypeScript: yes
- RSC: no (Vite SPA, not Next.js)

This creates `components.json`, `src/lib/utils.ts` (with `cn`), and updates `src/index.css` and `tsconfig.json`.

### 3.2 Path aliases

`tsconfig.app.json` adds:
```json
"baseUrl": ".",
"paths": { "@/*": ["./src/*"] }
```

`vite.config.ts` adds:
```ts
import path from "node:path";
// ...
resolve: { alias: { "@": path.resolve(__dirname, "./src") } }
```

### 3.3 New dependencies

shadcn init pulls in: `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `tw-animate-css`. Individual `shadcn add <component>` commands pull Radix primitives as needed (e.g. `@radix-ui/react-tabs`, `@radix-ui/react-avatar`, `@radix-ui/react-label`, `@radix-ui/react-separator`).

### 3.4 Apply ocean-breeze

```
npx shadcn@latest add https://tweakcn.com/r/themes/ocean-breeze.json
```

This overwrites the `:root` and `.dark` blocks in `src/index.css` with ocean-breeze's CSS variables (background, foreground, primary, secondary, muted, accent, destructive, border, input, ring, chart-1..5, radius, fonts).

### 3.5 Dark mode wiring

After theme install, edit `src/index.css` to wrap the `.dark` block in a media query so OS preference drives the theme without JS:

```css
@media (prefers-color-scheme: dark) {
  :root {
    /* contents of the .dark block ocean-breeze added */
  }
}
```

Delete the `.dark { ... }` block. If a toggle is wanted later, revert this change and re-add the class.

## 4. Primitive migration

All in `src/components/ui/`. shadcn primitives go in the same directory (its convention). Custom wrappers either replace the existing primitive entirely or compose shadcn ones.

### 4.1 shadcn primitives to install

```
npx shadcn@latest add button card input label tabs badge avatar separator
```

Each lands as `src/components/ui/<name>.tsx`. These are shadcn-owned files — edit them freely later; they're not a black-box library.

### 4.2 Wrapper / replacement strategy

| Existing file | After this pass |
|---|---|
| `Button.tsx` | Keep file. Reimplement as a thin wrapper around shadcn `Button`. Preserves the `to` prop branch that renders a react-router `<Link>` for SPA navigation. Variant mapping: `primary` → shadcn `default`, `secondary` → shadcn `outline`, `ghost` → shadcn `ghost`. Callsites unchanged. |
| `Card.tsx` | Keep file. Reimplement as a thin wrapper around shadcn `Card` (just `Card` + `CardContent` for the simple one-slot use case). Same `{ className?, children }` signature. |
| `FormField.tsx` | Keep file. Reimplement using shadcn `Label` + `Input`. Same `{ label, id, error?, ...inputProps }` signature. |
| `PageHeader.tsx` | Keep file. Same shape (`title`, `description?`, `action?`). Swap hardcoded color classes for semantic tokens (`text-foreground`, `text-muted-foreground`). |
| `EmptyState.tsx` | Keep file. Same shape. Swap `text-slate-500` for `text-muted-foreground`. |
| `TabStrip.tsx` | Keep file. Reimplement on top of shadcn `Tabs`. Same `{ tabs, paramName?, defaultKey? }` signature. Active tab still drives `?tab=` in the URL via `useSearchParams`. Caller still owns what renders for the active tab. |

The naming clash (existing `Button.tsx` vs shadcn `button.tsx`) is resolved by shadcn's lowercase file naming. We keep our wrappers Pascal-case (`Button.tsx`) and they import from `@/components/ui/button` (lowercase, shadcn).

### 4.3 New primitives pre-installed (not yet used in pages)

Installed for the style guide page and to unblock the next feature waves:
- `Badge` — streak counters, "coming soon" pills
- `Avatar` — user identity in feed / leaderboard / chat
- `Separator` — Settings page section dividers

## 5. Style guide route

New file: `src/pages/StyleGuide.tsx`.
New route: `/style-guide`, mounted outside `<AppLayout>` so the page is self-contained.

```tsx
// In App.tsx, alongside /auth (also outside AppLayout):
<Route path="/style-guide" element={<StyleGuide />} />
```

### 5.1 Sections (in order)

1. **Brand** — wordmark `synzoia`, tagline placeholder, a note that the logo will land later
2. **Colors** — swatches for every semantic token (background, foreground, primary, secondary, muted, accent, destructive, border, ring). Each swatch shows the variable name, the resolved color, and contrast against its paired foreground. Side-by-side light vs. dark columns so both palettes are visible regardless of OS preference (use inline `style={{ colorScheme: 'light' }}` and `'dark'` wrappers around each column to force).
3. **Typography** — h1, h2, h3, body, small, muted, with the class strings used
4. **Radii + spacing** — visual examples of `rounded-md`, `rounded-lg`, `rounded-xl`, and the `--radius` token shadcn uses
5. **Buttons** — every variant (default, outline, ghost, destructive if shadcn provides it) × every state (default, hover via :hover demo, disabled) × link-vs-button forms (the `to=` variant)
6. **Cards** — one with content, one with header + footer, one nested
7. **Form fields** — single field, field with error, field disabled
8. **Tabs** — `TabStrip` with 3 sample tabs wired to a fake `?demo=` param
9. **Empty states** — default message, custom message
10. **Badges** — every variant
11. **Avatars** — with image, with fallback initials

### 5.2 Page structure

```tsx
<div className="min-h-screen bg-background text-foreground">
  <header className="border-b border-border px-6 py-4">
    <h1 className="text-2xl font-semibold tracking-tight">synzoia style guide</h1>
    <p className="text-muted-foreground text-sm">v1 — ocean-breeze theme</p>
  </header>
  <main className="max-w-4xl mx-auto px-6 py-10 space-y-16">
    {/* Sections, each as <section> with an h2 */}
  </main>
</div>
```

Not linked from `AppLayout` nav. Discoverable via direct URL only. This keeps it out of the user-facing product surface while being trivially available during development.

## 6. Page restyle pass

For each of the 7 existing pages and `AppLayout`, apply the same find-and-replace pattern:

| Was | Becomes |
|---|---|
| `bg-white` (card surface) | `bg-card text-card-foreground` (or just `bg-card` if foreground inherits) |
| `bg-background` (hand-rolled token) | `bg-background` (semantic, now from ocean-breeze) |
| `text-slate-900` | `text-foreground` |
| `text-slate-500` | `text-muted-foreground` |
| `bg-indigo-600` | `bg-primary` |
| `hover:bg-indigo-700` | `hover:bg-primary/90` |
| `text-indigo-600` | `text-primary` |
| `border-slate-200` | `border-border` |
| `border-b border-slate-200` (active tab) | `border-b border-primary` |
| `rounded-2xl` (cards) | `rounded-xl` (matches shadcn `--radius`) |

Page shapes from the shallow pass are preserved. The only structural change is that the wordmark in `AppLayout` may be marked up with a `data-logo-slot` attribute so swapping in an `<img>` tonight is a one-line edit:

```tsx
<Link to="/crews" className="flex items-center gap-2">
  <span data-logo-slot className="text-lg font-semibold tracking-tight">synzoia</span>
</Link>
```

## 7. File structure

```
frontend/
├── components.json                       # NEW (shadcn config)
├── vite.config.ts                        # UPDATED (path alias)
├── tsconfig.app.json                     # UPDATED (path alias)
├── package.json                          # UPDATED (new deps)
└── src/
    ├── App.tsx                           # UPDATED (+ /style-guide route)
    ├── index.css                         # REWRITTEN (ocean-breeze tokens + media-query dark)
    ├── lib/
    │   └── utils.ts                      # NEW (cn helper from shadcn init)
    ├── components/
    │   ├── layout/
    │   │   └── AppLayout.tsx             # UPDATED (semantic tokens, data-logo-slot)
    │   └── ui/
    │       ├── button.tsx                # NEW (shadcn)
    │       ├── card.tsx                  # NEW (shadcn)
    │       ├── input.tsx                 # NEW (shadcn)
    │       ├── label.tsx                 # NEW (shadcn)
    │       ├── tabs.tsx                  # NEW (shadcn)
    │       ├── badge.tsx                 # NEW (shadcn)
    │       ├── avatar.tsx                # NEW (shadcn)
    │       ├── separator.tsx             # NEW (shadcn)
    │       ├── Button.tsx                # UPDATED (wraps shadcn button)
    │       ├── Card.tsx                  # UPDATED (wraps shadcn card)
    │       ├── FormField.tsx             # UPDATED (composes Label + Input)
    │       ├── PageHeader.tsx            # UPDATED (semantic tokens)
    │       ├── EmptyState.tsx            # UPDATED (semantic tokens)
    │       └── TabStrip.tsx              # UPDATED (built on shadcn Tabs)
    └── pages/
        ├── Auth.tsx                      # UPDATED (semantic tokens)
        ├── Crews.tsx                     # UPDATED
        ├── CrewDetail.tsx                # UPDATED
        ├── PostSleep.tsx                 # UPDATED
        ├── UserProfile.tsx               # UPDATED
        ├── Settings.tsx                  # UPDATED
        ├── Home.tsx                      # unchanged (pure redirect)
        └── StyleGuide.tsx                # NEW
```

## 8. Testing impact

- The existing 11 smoke tests stay green (route h1 assertions still hold; no h1 changes in any page).
- Add one new assertion: `/style-guide` renders an h1.
- Final count: **12 tests**.

No new test infrastructure. No new mocks.

## 9. Acceptance checks

After this lands:

1. `npm run typecheck`, `npm run lint`, `npm run test` (12 tests), `npm run build` all exit 0.
2. In dev server, every route renders with ocean-breeze tokens in light mode (warm-cool ocean palette, not the old indigo).
3. Toggling OS appearance to dark flips the entire app (background, surfaces, text, accents) to ocean-breeze's dark variant. No layout shift.
4. `/style-guide` renders all 11 sections; every primitive appears in every documented variant + state.
5. Grep finds no remaining `bg-indigo-`, `text-slate-`, `border-slate-`, `bg-white` strings inside `src/pages/` or `src/components/layout/` (semantic tokens replace them all).
6. The wordmark `synzoia` in `AppLayout` is wrapped in an element with `data-logo-slot` for easy logo swap.
7. The shallow-pass acceptance checks (route h1s, redirect, tab URL behavior, disabled buttons) all still pass.

## 10. Things to push back on if I drift during implementation

- Don't manually rewrite ocean-breeze's variables — let the `shadcn add` command do it.
- Don't add a toggle UI for dark mode. System default only for v1.
- Don't link `/style-guide` from the user-facing nav.
- Don't bring in icons beyond what shadcn imports automatically. Logo + icon system is its own pass.
- Don't add `<Form>`, `<Toast>`, `<Modal>` primitives. None of the existing pages need them; they land with real flows.
- Don't replace `useSearchParams`-based `TabStrip` with internal state. URL state for tab selection is a hard rule from `CLAUDE.md`.
