# SP2 — Coastal Theme Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the "Sandalwood & Sea" coastal design language the app's theme foundation (light + dark) by adopting the palette already drafted on the `coastal-redesign` branch, switching to the mockup fonts, and defaulting to the light coastal look, so SP3 pages and SP4 messages build on it.

**Architecture:** The app is Tailwind v4 + shadcn-style tokens in `frontend/src/index.css`; components consume tokens via utility classes (no hardcoded colors), so swapping token values restyles the whole app. The `coastal-redesign` branch already mapped the Sandalwood palette into those tokens (light + dark) and added coastal utilities (`surface-glass`, `label-mono`, `glass-bar`, `pill`, washes). SP2 adopts that palette, fixes the one thing the branch left undone (fonts), flips the default theme to light, applies serif headings + a teal logo accent, and showcases everything in the existing StyleGuide.

**Tech Stack:** React + TypeScript + Vite, Tailwind CSS v4, shadcn/ui patterns, Google Fonts, vitest, eslint.

## Global Constraints

- **Palette = "Sandalwood & Sea"** exact mockup hexes (light): bg `#f8f1e7`, surface `#fdfaf6`/`#f3ece1`, primary teal `#1a9b8f` (dk `#157a70`, lt `#d6f4f1`), green `#2d6a4f`, amber `#c68642`, bark `#7a3e28`, fern `#1e4d2b`, text `#1a2620`/`#4a5e56`/muted `#7a8f84`, border `#d4c9b6`/`#e8e0d2`. Source of the OKLCH conversions: `git show coastal-redesign:frontend/src/index.css`.
- **Fonts (mockup set):** serif `Cormorant Garamond` (headings, italic accents); sans/body `Plus Jakarta Sans`; mono `Space Mono` (small uppercase labels/chips). No `Lora`, `DM Sans`, or `IBM Plex Mono` may remain.
- **Radius scale:** base `--radius: 0.75rem` (12px); large surfaces use the existing `surface-glass` (20px).
- **Keep both light + dark.** Default = follow OS preference, fallback light (the coastal light look). Toggle + persistence stay working.
- **Token-driven only.** No hardcoded hex/rgb in components; route all color through tokens.
- **No component-contract changes.** Visual/token only; existing props and existing tests must still pass.
- **Scope:** tokens + fonts + shared primitives + app shell + StyleGuide ONLY. No page-layout rebuilds (SP3), no messages (SP4), no backend/API/Supabase changes.
- **Testing note (visual work):** classic TDD does not fit CSS/visual changes. Verification per task = build + typecheck + lint + existing vitest suite pass + visual check in the StyleGuide (light and dark). One real guard test is added for the font switch. Do NOT write assertion-free or brittle "the background is sand" tests.
- Commit messages end with the `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.

---

### Task 1: Adopt the Sandalwood palette, switch fonts, default to light

**Files:**
- Modify: `frontend/src/index.css` (token values + font tokens + radius)
- Modify: `frontend/index.html` (font `<link>` + theme-init script)
- Create: `frontend/src/__tests__/theme-fonts.test.ts` (font-switch guard)

**Interfaces:**
- Produces: the full coastal token set (light `:root` + dark `:root.dark`) with `--font-sans/serif/mono` set to the mockup families and `--radius: 0.75rem`. Later tasks and all components rely on these tokens.

- [ ] **Step 1: Write the failing guard test**

Create `frontend/src/__tests__/theme-fonts.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../..');           // frontend/
const indexHtml = readFileSync(resolve(root, 'index.html'), 'utf8');
const indexCss = readFileSync(resolve(root, 'src/index.css'), 'utf8');

describe('coastal fonts are wired and old fonts are gone', () => {
  it('index.html loads the three mockup fonts', () => {
    expect(indexHtml).toContain('Cormorant+Garamond');
    expect(indexHtml).toContain('Plus+Jakarta+Sans');
    expect(indexHtml).toContain('Space+Mono');
  });
  it('no old font families remain anywhere in theme files', () => {
    for (const stale of ['Lora', 'DM Sans', 'DM+Sans', 'IBM Plex Mono', 'IBM+Plex+Mono']) {
      expect(indexHtml).not.toContain(stale);
      expect(indexCss).not.toContain(stale);
    }
  });
  it('index.css font tokens use the coastal families', () => {
    expect(indexCss).toContain('"Cormorant Garamond"');
    expect(indexCss).toContain('"Plus Jakarta Sans"');
    expect(indexCss).toContain('"Space Mono"');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/__tests__/theme-fonts.test.ts`
Expected: FAIL (current files still use Lora/DM Sans/IBM Plex Mono).

- [ ] **Step 3: Adopt the Sandalwood palette into index.css**

Replace the palette in `frontend/src/index.css` with the branch's. Concretely: view `git show coastal-redesign:frontend/src/index.css` and copy its `:root` token block, its `:root.dark` block, the earthy extras (`--fern`, `--bark`, `--amber`, etc.), and the dark ambient-backdrop base rule, into the current `index.css` — replacing the current (marine/blue) `:root` and `.dark` palette values. Leave the `@theme inline` map, the utility classes (`surface-glass`, `label-mono`, `glass-bar`, `pill`, washes, animations) as they already are (they are identical). Do NOT bring over any `Landing.tsx` change.

- [ ] **Step 4: Set the coastal font tokens + radius in index.css**

In the `:root` block of `frontend/src/index.css`, set these three lines (replacing the old families) and the radius:

```css
  --radius: 0.75rem;
  --font-sans: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --font-serif: "Cormorant Garamond", Georgia, serif;
  --font-mono: "Space Mono", ui-monospace, monospace;
```

- [ ] **Step 5: Swap the font `<link>` in index.html**

In `frontend/index.html`, replace the existing Google Fonts `<link rel="stylesheet" ...>` href with:

```
https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500&family=Plus+Jakarta+Sans:wght@300;400;500;600&family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap
```

Keep the two `preconnect` links above it unchanged.

- [ ] **Step 6: Default the theme to follow OS (fallback light) in index.html**

Replace the inline `<script>` theme-init block in `frontend/index.html` with:

```html
<script>
  (function () {
    try {
      var stored = window.localStorage.getItem('synzoia.theme');
      var prefersDark =
        window.matchMedia &&
        window.matchMedia('(prefers-color-scheme: dark)').matches;
      var theme =
        stored === 'light' || stored === 'dark'
          ? stored
          : prefersDark
            ? 'dark'
            : 'light';
      if (theme === 'dark') document.documentElement.classList.add('dark');
    } catch (e) {
      /* default = light coastal: add nothing */
    }
  })();
</script>
```

This matches `useTheme`'s documented "Default = OS preference" (so no flash/flip on mount) and removes the old dark-first bias. `frontend/src/hooks/useTheme.ts` needs no change.

- [ ] **Step 7: Run the guard test + full font grep**

Run: `cd frontend && npx vitest run src/__tests__/theme-fonts.test.ts`
Expected: PASS.
Run: `cd frontend && grep -rIn -E 'Lora|DM[ +]Sans|IBM[ +]Plex[ +]Mono' index.html src`
Expected: no output (no old fonts anywhere).

- [ ] **Step 8: Build to confirm the theme compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds (Tailwind v4 + Vite), no CSS errors.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/index.css frontend/index.html frontend/src/__tests__/theme-fonts.test.ts
git commit -m "feat(theme): adopt Sandalwood & Sea palette + coastal fonts, default light

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Serif headings + teal logo accent

**Files:**
- Modify: `frontend/src/components/ui/PageHeader.tsx` (heading → serif)
- Modify: `frontend/src/components/layout/AppLayout.tsx` (logo teal accent letter)

**Interfaces:**
- Consumes: `--font-serif` (Cormorant Garamond) + `font-display` utility + `text-primary` token from Task 1.
- Produces: shared page heading style and the branded logo used across all pages.

- [ ] **Step 1: Make the PageHeader title use the serif display font**

In `frontend/src/components/ui/PageHeader.tsx`, change the `h1` className from
`text-2xl font-semibold tracking-tight text-foreground` to:

```tsx
        <h1 className="font-display text-3xl tracking-tight text-foreground">{title}</h1>
```

(`font-display` is the serif utility defined in `index.css`.) Leave the `description` and `action` markup unchanged.

- [ ] **Step 2: Add the teal accent letter to the logo**

In `frontend/src/components/layout/AppLayout.tsx`, replace the logo span's text `synzoia` so the `z` carries the primary color (matches the mockup `.logo span { color: var(--primary) }`):

```tsx
            <span
              data-logo-slot
              className="font-display italic text-xl tracking-tight text-foreground"
            >
              syn<span className="text-primary">z</span>oia
            </span>
```

- [ ] **Step 3: Typecheck + build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both pass.

- [ ] **Step 4: Run the existing component test suite (no contract regressions)**

Run: `cd frontend && npx vitest run`
Expected: all existing tests pass (including the Task 1 font guard and `SleepPost.test.tsx`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/PageHeader.tsx frontend/src/components/layout/AppLayout.tsx
git commit -m "feat(theme): serif page headings + teal logo accent

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: StyleGuide coverage for every primitive in both themes

**Files:**
- Modify: `frontend/src/pages/StyleGuide.tsx`

**Interfaces:**
- Consumes: all themed primitives + tokens from Tasks 1-2.
- Produces: the visual review surface used to sign off SP2 (and a reference for SP3).

- [ ] **Step 1: Audit current StyleGuide coverage**

Read `frontend/src/pages/StyleGuide.tsx`. It already showcases color tokens, typography (`font-display`, `label-mono`), `Button`, `Card`, `FormField`, `EmptyState`, `TabStrip`, `Badge`, `Avatar`. List which shared primitives are NOT yet shown (check against `components/ui/`: at minimum `input`, `label`, `tabs`, `badge` variants, `separator`, `ErrorCard`, `DailyBars`).

- [ ] **Step 2: Add a section rendering each missing primitive**

For every primitive identified in Step 1, add a `Spread`/section to `StyleGuide.tsx` that renders it with realistic props, following the existing `Spread` pattern already in the file. Show `Badge` in each variant (`default`, `secondary`, `outline`, `ghost`, `destructive`), and an `input` + `label` pairing. Use only token-driven classes (no hardcoded colors).

- [ ] **Step 3: Typecheck + build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both pass.

- [ ] **Step 4: Visual check in light and dark**

Run: `cd frontend && npm run dev`, open the StyleGuide route (`/style` or as routed in `App.tsx` — confirm the path), and verify every primitive reads as coastal in BOTH themes (toggle via the nav). Confirm: sand background, teal primary, Cormorant Garamond headings, Space Mono labels, soft warm cards. Note any primitive that looks wrong for a follow-up fix in this task.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/StyleGuide.tsx
git commit -m "feat(theme): StyleGuide showcases all primitives in light + dark

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Full verification + preview deploy

**Files:** none (gates + PR).

**Interfaces:**
- Consumes: the complete SP2 branch.
- Produces: a green CI run and a Vercel preview URL for visual sign-off before production.

- [ ] **Step 1: Run every CI gate locally**

Run: `cd frontend && npm run lint && npm run typecheck && npx vitest run && npm run build`
Expected: all pass. Fix anything that fails before proceeding.

- [ ] **Step 2: Push the branch + open a PR**

```bash
git push -u origin worktree-sp2-coastal-theme
gh pr create --repo rmbriggs/synzoia --base main --head worktree-sp2-coastal-theme \
  --title "feat: SP2 coastal theme foundation (Sandalwood & Sea + fonts)" \
  --body "Adopts the Sandalwood & Sea palette + coastal fonts, defaults to light, serif headings, teal logo accent, StyleGuide coverage. Page layouts unchanged (SP3). Preview deploy for visual review."
```

- [ ] **Step 3: Watch CI**

Run: `gh pr checks --repo rmbriggs/synzoia worktree-sp2-coastal-theme --watch`
Expected: `backend` + `frontend` checks pass.

- [ ] **Step 4: Get the Vercel preview URL + verify it is coastal**

Find the preview deployment for this branch (`vercel ls synzoia`, or the Vercel bot comment on the PR). Open it and confirm the live preview shows the coastal theme (light by default, dark via toggle) with the new fonts, on the existing page layouts. Report the preview URL.

- [ ] **Step 5: Stop for review**

Do NOT merge to production automatically. Report: CI status, the preview URL, and a short note that layouts are intentionally unchanged until SP3. Await go-ahead to merge (merge triggers the production deploy).

---

## Self-Review

**Spec coverage:**
- Palette (light) into shadcn tokens → Task 1 (adopt branch palette). ✓
- Dark coastal palette refined/kept → Task 1 (adopt branch `:root.dark`). ✓
- Fonts switched to Cormorant/Jakarta/Space Mono → Task 1 (tokens + index.html) + guard test. ✓
- Radius/shadow scale → Task 1 (`--radius: 0.75rem`; warm shadows already in branch index.css). ✓
- Default theme = light/OS (mockups are light) → Task 1 Step 6. ✓
- Shared primitives in coastal language → token-driven (auto) + Task 2 (headings/logo); audited in Task 3. ✓
- App shell (nav, ThemeToggle) → already coastal; logo accent in Task 2; ThemeToggle unchanged (token-driven). ✓
- StyleGuide showcase (light + dark) → Task 3. ✓
- Verification: CI gates + preview deploy → Task 4; existing tests guarded in Task 2 Step 4. ✓
- No page-layout/backend changes → enforced by Global Constraints; no task touches pages beyond StyleGuide or backend. ✓

**Placeholder scan:** No TBD/TODO. Exact font href, token lines, theme script, JSX edits, and test code are all inline. The palette adoption points to a committed in-repo source (`coastal-redesign` index.css) rather than re-transcribing ~100 OKLCH lines — that is a concrete source, not a placeholder.

**Type/name consistency:** `font-display` (serif utility), `label-mono`, `surface-glass`, `--font-sans/serif/mono`, `text-primary` used consistently across tasks and match the existing `index.css` definitions and `AppLayout`/`StyleGuide` usage. Branch name `worktree-sp2-coastal-theme` consistent in Task 4.

## Notes / Open Risks

- **StyleGuide route path** is referenced as `/style` in Task 3 Step 4 but must be confirmed against `App.tsx` routing during execution.
- **OKLCH vs mockup hex drift:** the branch's conversions are approximate; the StyleGuide visual check (Task 3) + preview (Task 4) are where any off color gets caught and nudged.
- **Dark mode contrast:** spot-check text/surface/primary in dark during Task 3 Step 4 since the mockups give no dark reference.
