# SP2 — Coastal Theme Foundation Design

**Date:** 2026-06-17
**Status:** Approved (design); implementation plan pending
**Owner:** rmbriggs (Micah)

## Context

Second of four sub-projects applying the "Santa Cruz coastal" design from
`SamM-UATX/synzoia-mockups` to the real React app. SP1 (repo + hosting migration)
is complete; the app now lives at `rmbriggs/synzoia` and deploys to
`synzoia.vercel.app`. See [[project_synzoia_coastal_redesign]].

- SP1 — repo + hosting migration. DONE.
- **SP2 — coastal theme foundation (this doc).** Tokens (color/font/radius/shadow,
  light + dark) + shared primitives + app shell.
- SP3 — page redesigns (Landing, Feed, Profile, Leaderboard, Users).
- SP4 — Messages feature (net-new).

A local branch `coastal-redesign` (one commit, off `f9ce623`) already did real work:
it mapped the mockup palette into the existing shadcn OKLCH token system for **both**
light and dark (`:root` and `:root.dark` blocks in `frontend/src/index.css`). It did
**not** switch the fonts (still DM Sans / Lora / IBM Plex Mono) and only touched
`index.css` + `Landing.tsx`. SP2 builds on its theme work and sets the `Landing.tsx`
rewrite aside for SP3.

## Current state (verified 2026-06-17)

- **Styling system:** Tailwind v4 (`@import "tailwindcss"`) with shadcn-style CSS
  variables in `frontend/src/index.css` (`--background`, `--primary`, `--card`,
  `--font-sans/serif/mono`, radius, shadow tokens), mapped via `@theme inline`.
- **Fonts:** loaded with a Google Fonts `<link>` in `frontend/index.html` (currently
  `Lora`, `DM Sans`, `IBM Plex Mono`). No font npm packages. The `--font-*` tokens in
  `index.css` name those families.
- **Dark mode:** real feature. `ThemeToggle` (`frontend/src/components/layout/ThemeToggle.tsx`)
  toggles a `dark` class on `:root`; `index.css` has `.dark` token blocks.
- **Shared primitives:** `frontend/src/components/ui/*` (AppCard, AppButton, button,
  card, badge, input, label, tabs, TabStrip, separator, PageHeader, DailyBars,
  EmptyState, ErrorCard, FormField, skeletons) and `frontend/src/components/layout/*`
  (AppLayout, ThemeToggle).
- **Visual review surface:** `frontend/src/pages/StyleGuide.tsx` already exists.
- **CI gates:** eslint + typecheck + vitest + build (frontend job); lint is enforced.

## Goal

Make the "Sandalwood & Sea" coastal language the app's theme foundation (light + dark)
so SP3 pages and SP4 messages build on one consistent, mockup-aligned base. After SP2
ships, the live site looks clearly coastal (new palette, fonts, components) while page
**layouts remain the current ones** until SP3. That is the intended incremental state.

## Design decisions

**Palette — "Sandalwood & Sea" (light), exact mockup values:**
- Backgrounds: `--bg #f8f1e7`, `--bg-alt #efe7d8`, `--bg-deep #e6dccf`
- Surfaces: `--surface #fdfaf6`, `--surface-2 #f3ece1`
- Primary (Pacific teal): `#1a9b8f`, dk `#157a70`, lt `#d6f4f1`
- Accents: green `#2d6a4f`/lt `#daeee5`; amber `#c68642`/lt `#f5e8d3`;
  bark/redwood `#7a3e28`/dk `#5c2c18`/lt `#f2e0d4`; fern `#1e4d2b`/mid `#2a5c38`/lt `#cce3d4`
- Text: `#1a2620` / `--text-2 #4a5e56` / `--muted #7a8f84`
- Borders: `--border #d4c9b6`, `--border-lt #e8e0d2`

These map onto the shadcn token names (`--background`, `--foreground`, `--card`,
`--primary`, `--secondary`, `--muted`, `--accent`, `--border`, `--ring`, etc.). Reuse
the `coastal-redesign` branch's OKLCH conversions where they already match these
hexes; correct any that drift. Earthy accents (bark/fern/amber/green) are added as
extra tokens for component use.

**Dark mode — coastal night:** keep the toggle. Refine the branch's `:root.dark`
palette into a coherent dark coastal theme (deep forest/bark ground, sand-tinted text,
teal primary that holds contrast). Every shadcn token defined in light must have a dark
counterpart that passes basic contrast.

**Fonts — mockup set:**
- Serif (`--font-serif`): `Cormorant Garamond` — headings and italic accents.
- Sans / body (`--font-sans`): `Plus Jakarta Sans`.
- Mono (`--font-mono`): `Space Mono` — small uppercase labels and chips.
- Implementation: update the `<link>` in `frontend/index.html` to load these three
  (weights/italics per the mockups), and update the `--font-*` tokens in `index.css`.
  Base element styling: headings use the serif; small label/eyebrow/chip text uses mono
  uppercase with letter-spacing, matching the mockups.

**Shape + elevation:** radius scale `12px / 20px / 32px` (mockup `--radius`,
`--radius-lg`, `--radius-xl`) mapped onto the existing `--radius` token family; soft
warm low-opacity shadows.

## Scope

**In scope (SP2):**
- `frontend/src/index.css` — full token system (light + dark), base element styling.
- `frontend/index.html` — font `<link>`.
- Shared primitives restyle: card/AppCard, button/AppButton, badge, input, label,
  tabs/TabStrip, separator, PageHeader, EmptyState/ErrorCard, skeletons, DailyBars.
- App shell: `AppLayout` nav (sticky, blurred sand bar; serif-italic "synzoia" logo
  with a teal accent letter; Space-Mono nav chips) and `ThemeToggle` styling.
- `StyleGuide.tsx` — extend to showcase every themed primitive (light + dark) as the
  review surface.

**Out of scope (later):**
- Full page layout rebuilds for Landing, Feed, Profile, Leaderboard, Users — SP3.
- The `coastal-redesign` branch's `Landing.tsx` rewrite — cherry-picked/redone in SP3.
- Messages UI/feature — SP4.
- Backend, Supabase, API changes — none.

## Components / units

- **Token layer** (`index.css`, `index.html`): single source of color/font/radius/
  shadow truth. Consumers reference tokens only; no hardcoded hexes in components.
- **Primitive layer** (`components/ui/*`): each component reads tokens; visual change
  only, public props/interfaces unchanged so SP3/existing pages keep working.
- **Shell layer** (`components/layout/*`): nav + theme toggle, token-driven.
- **Showcase** (`StyleGuide.tsx`): renders all primitives for visual diffing.

## Verification

- `StyleGuide` page shows every primitive in light and dark for visual review.
- CI gates: `npm run lint`, typecheck, `vitest --run`, `build` all pass.
- Existing component tests (e.g. `SleepPost.test.tsx`) still pass — restyle must not
  change component contracts.
- Preview deploy (Vercel preview URL from the SP2 PR) for live visual review before
  production.

## Non-goals

- No new pages or layout changes (SP3).
- No new features (SP4).
- No backend/API/Supabase changes.
- No change to component props/behavior — visual/token only.

## Risks & mitigations

- **Hardcoded colors in components** bypassing tokens. Mitigation: grep for hex/`rgb`
  literals in `components/` and route them through tokens during the restyle.
- **Dark mode contrast** since mockups give no dark reference. Mitigation: derive dark
  from the branch's start, spot-check contrast on text/surfaces/primary in StyleGuide.
- **Font loading flash / weight gaps.** Mitigation: `display=swap`, load only the
  weights the mockups use, keep system-font fallbacks in the token values.
- **Scope creep into page layouts.** Mitigation: the scope boundary above; pages keep
  their current structure in SP2.

## Success criteria

- `index.css` + `index.html` carry the full Sandalwood & Sea token set (light + dark)
  and the three mockup fonts; no old fonts (Lora/DM Sans/IBM Plex Mono) remain.
- Shared primitives + nav render in the coastal language, driven only by tokens.
- StyleGuide showcases all primitives in both themes; CI green; preview deploy looks
  coastal.
- Existing pages still function (rethemed, not relaid-out); no component-contract
  changes.
