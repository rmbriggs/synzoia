# synzoia frontend — Shallow design pass

**Date**: 2026-05-18
**Owner**: Micah (sole frontend + design owner)
**Scope**: Build out a shallow but coherent shell for all 7 routes. Data-bearing sections show "coming soon" empty states; non-data UI (forms, buttons, layout) is real. Visual identity is a deliberately conservative placeholder; full style guide lands in a later session.
**Parent specs**:
- Project design: [`2026-05-16-synzoia-design.md`](./2026-05-16-synzoia-design.md)
- Scaffolding design: [`2026-05-17-frontend-scaffolding-design.md`](./2026-05-17-frontend-scaffolding-design.md)

---

## 1. Goal

After the scaffold landed in PR #1, every route renders a single `<h1>` against an unstyled white page. This pass makes every route look like a real product page — with shared layout chrome, a small primitive library, and a coherent (if placeholder) palette and typography — without doing any real backend wiring. Where data would render, the user sees a "coming soon" empty state. Where input would happen (auth, post-sleep, settings), the form shape is visible but submit buttons are disabled.

**Why shallow not deep:** the backend is still unbuilt. Real flows can't be tested end-to-end yet. The goal here is to lock in the layout, component patterns, and overall product feel so that when backend slices land, plugging them in is a small change rather than a redesign.

**Out of scope (later sessions):**
- Real auth flow (`useAuthSession` stays a stub returning `{session: null, loading: false}`)
- Real API calls (every page is a stub that imports nothing from `api/client.ts` yet)
- Final visual identity (palette, type scale, vibe) — owner plans a dedicated style-guide pass
- Animations, transitions, micro-interactions
- Icons, illustrations, photography
- Accessibility audit (basic semantic HTML + sr-only labels only)
- Loading skeletons (we have "coming soon" instead until backend exists)

## 2. Visual approach

Calm-minimal indigo placeholder. Off-white background, indigo primary, slate text, generous spacing, rounded-2xl cards. The intent is "looks like a real product, doesn't fight the proper style guide that lands later." We deliberately avoid heavy custom tokens so the eventual style guide doesn't have to undo decisions.

## 3. Design tokens

`index.css` becomes:

```css
@import "tailwindcss";

@theme {
  --color-background: oklch(99% 0.003 95);   /* warm off-white */
  --radius-card: 1rem;
}

html, body, #root {
  height: 100%;
}

body {
  @apply bg-background text-slate-900 antialiased;
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", system-ui, sans-serif;
}
```

Everything else is Tailwind utilities applied at component callsites. The canonical patterns:

| Use | Class |
|---|---|
| Card surface | `bg-white border border-slate-200 rounded-2xl p-6` |
| Primary button | `bg-indigo-600 hover:bg-indigo-700 text-white` |
| Secondary button | `bg-white border border-slate-200 hover:bg-slate-50 text-slate-900` |
| Ghost button | `text-slate-600 hover:text-slate-900` |
| Page title | `text-2xl font-semibold tracking-tight` |
| Section title | `text-lg font-semibold` |
| Body text | default (`text-slate-900`) |
| Muted text | `text-slate-500` |
| Disabled state | `opacity-50 cursor-not-allowed` |
| Active tab indicator | `border-b-2 border-indigo-600` |

When the proper style-guide pass lands, all of this becomes named tokens in `@theme` and the utility class strings collapse into semantic component variants. Until then, keep it pragmatic.

## 4. Layout chrome

One shared layout component, `src/components/layout/AppLayout.tsx`, wraps every logged-in route. `/auth` skips it.

```
DESKTOP (≥ 640px)                  MOBILE (< 640px)
┌──────────────────────────────┐    ┌──────────────────┐
│ synzoia          [Settings]  │    │     synzoia       │
├──────────────────────────────┤    ├──────────────────┤
│                              │    │                  │
│   <Outlet />                 │    │   <Outlet />     │
│   max-w-2xl mx-auto px-6 py-6│    │   px-4 py-4      │
│                              │    │                  │
│                              │    ├──────────────────┤
│                              │    │ Crews | Settings │
└──────────────────────────────┘    └──────────────────┘
```

**Top bar** (always visible):
- Thin sticky header: `bg-background border-b border-slate-200 sticky top-0 z-10`
- Wordmark "synzoia" on left, links to `/crews` (`text-lg font-semibold tracking-tight`)
- Right side: on desktop (`sm:` and up), a `<Link to="/settings">Settings</Link>`. On mobile, right side is empty.

**Main**:
- `<main className="max-w-2xl mx-auto px-4 sm:px-6 py-6 pb-24 sm:pb-6">`
- The `pb-24` on mobile gives clearance for the fixed bottom tab bar.
- Renders `<Outlet />` from React Router.

**Bottom tab bar** (mobile only, `sm:hidden`):
- `fixed bottom-0 inset-x-0 bg-white border-t border-slate-200`
- Two `<NavLink>`s: **Crews** (`to="/crews"`), **Settings** (`to="/settings"`)
- Active link gets `text-indigo-600`; inactive gets `text-slate-500`
- Each link is `flex-1 py-3 text-center text-sm font-medium`
- `pb-[env(safe-area-inset-bottom)]` so iOS home-indicator doesn't overlap

Text-only labels. Icons land with the proper style guide.

**`App.tsx`** restructures to wrap logged-in routes in `<Route element={<AppLayout/>}>`:

```tsx
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
```

## 5. Reusable primitives

All in `src/components/ui/`. Every component is < 50 lines.

| File | Props | Behavior |
|---|---|---|
| `Card.tsx` | `className?: string`, `children` | `<div className="bg-white border border-slate-200 rounded-2xl p-6 {className}">{children}</div>` |
| `PageHeader.tsx` | `title: string`, `description?: string`, `action?: ReactNode` | `<h1>` + optional `<p>` + optional right-aligned slot for an action button |
| `Button.tsx` | `variant: 'primary' | 'secondary' | 'ghost'`, `disabled?: boolean`, `children`, and EITHER `{ onClick?, type? }` (renders `<button>`) OR `{ to: string }` (renders react-router-dom's `<Link>` for SPA navigation) | Variant-driven classes per §3. Internal links use `to`; external links would need a future variant — none yet. |
| `EmptyState.tsx` | `message?: string` (default: "Coming soon") | Centered, `py-12`, `text-slate-500 text-sm` |
| `TabStrip.tsx` | `tabs: { key: string; label: string }[]`, `paramName?: string` (default: `'tab'`), `defaultKey?: string` | Reads/writes `?tab=` from URL via `useSearchParams`; rendering is just the bar — caller decides what to render for the active tab |
| `FormField.tsx` | `label: string`, `id: string`, `error?: string`, `type?`, and pass-through input props | Labeled `<input>` with consistent styling; `<label htmlFor>` accessibility |

No `<Form>`, `<Modal>`, `<Toast>`, or `<List>` — none of tonight's pages need them. They land when real flows do.

## 6. Per-page shapes

### 6.1 `/` — `Home.tsx`

Pure redirect, no visible UI.

```tsx
const { session, loading } = useAuthSession();
if (loading) return <p className="p-6">Loading…</p>;
return <Navigate to={session ? '/crews' : '/auth'} replace />;
```

Tonight's stub: `useAuthSession` returns `{session: null, loading: false}`, so `/` always redirects to `/auth`.

### 6.2 `/auth` — `Auth.tsx`

No `AppLayout`. Full-bleed centered card.

```
┌──────────────────────────────────────┐
│                                      │
│         (vertical center)            │
│   ┌──────────────────────────────┐   │
│   │       synzoia (h1)           │   │
│   │     Sleep with friends.      │   │
│   │                              │   │
│   │   [Email          ]          │   │
│   │   [Password       ]          │   │
│   │                              │   │
│   │   [    Sign in       ]       │   │
│   │                              │   │
│   │   Don't have an account?     │   │
│   │   Sign up                    │   │
│   └──────────────────────────────┘   │
│                                      │
└──────────────────────────────────────┘
```

Page wrapper: `min-h-screen flex items-center justify-center px-4`. Card max-width: `max-w-sm w-full`. Tagline: `text-slate-500 text-center mt-1`.

Two `<FormField>` (Email, Password). When the user clicks "Sign up", a `useState` flips the form into a 3-field variant adding "Display name" above email. Primary button "Sign in" / "Sign up" — `disabled` for now.

Toggle text below the button: "Don't have an account? **Sign up**" / "Already have one? **Sign in**" — the bold word is a button styled as a link (`text-indigo-600 hover:underline`).

### 6.3 `/crews` — `Crews.tsx`

```tsx
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
```

### 6.4 `/crews/:id` — `CrewDetail.tsx`

```tsx
const { id } = useParams();
const [params] = useSearchParams();
const activeTab = params.get('tab') ?? 'feed';

<PageHeader
  title={`Crew ${id}`}
  description="Real crew name lands when backend's ready."
  action={
    <Button variant="primary" to={`/crews/${id}/post`}>
      Post sleep
    </Button>
  }
/>
<TabStrip
  tabs={[
    { key: 'feed', label: 'Feed' },
    { key: 'leaderboard', label: 'Leaderboard' },
    { key: 'chat', label: 'Chat' },
  ]}
  defaultKey="feed"
/>
<Card className="mt-6">
  {activeTab === 'feed' && <EmptyState message="Feed coming soon — posts from this crew will appear here." />}
  {activeTab === 'leaderboard' && <EmptyState message="Leaderboard coming soon — weekly rankings." />}
  {activeTab === 'chat' && <EmptyState message="Chat coming soon — group thread for this crew." />}
</Card>
```

The "Post sleep" button is a real link to `/crews/:id/post`. Clicking it navigates; no backend needed. The PostSleep page itself shows the form shape but its submit is disabled.

### 6.5 `/crews/:id/post` — `PostSleep.tsx`

```tsx
<PageHeader
  title="Post your sleep"
  description="How'd you sleep last night?"
/>
<Card className="mt-6 space-y-4">
  <FormField id="bedtime" label="Bedtime" type="datetime-local" disabled />
  <FormField id="wake" label="Wake time" type="datetime-local" disabled />
  <FormField id="quality" label="Quality (1–100)" type="number" min={1} max={100} disabled />
  <FormField id="note" label="Note (optional, up to 280 chars)" type="text" disabled />
  <div className="flex gap-3 pt-2">
    <Button variant="primary" disabled>Post</Button>
    <Button variant="ghost" to={`/crews/${id}`}>Cancel</Button>
  </div>
</Card>
```

Phone full-screen affordance per spec §7 is deferred — current shape works on phone widths; we revisit when real form behavior lands.

### 6.6 `/users/:id` — `UserProfile.tsx`

```tsx
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
```

### 6.7 `/settings` — `Settings.tsx`

```tsx
<PageHeader title="Settings" />
<Card className="mt-6 space-y-4">
  <h2 className="text-lg font-semibold">Profile</h2>
  <FormField id="display-name" label="Display name" disabled />
  <FormField id="timezone" label="Timezone" disabled />
  <Button variant="primary" disabled>Save</Button>
</Card>
<Card className="mt-4">
  <h2 className="text-lg font-semibold">Sign out</h2>
  <p className="text-slate-500 text-sm mt-1">Sign out of synzoia on this device.</p>
  <Button variant="secondary" className="mt-3" disabled>Sign out</Button>
</Card>
<Card className="mt-4">
  <h2 className="text-lg font-semibold">About</h2>
  <p className="text-slate-500 text-sm mt-1">
    synzoia v0.0 — built for UATX Software Engineering Spring 2026.
  </p>
</Card>
```

## 7. File structure

```
frontend/src/
├── App.tsx                       # updated: nested routes under <AppLayout/>
├── main.tsx                      # unchanged
├── index.css                     # updated: @theme tweaks, body classes
├── components/
│   ├── layout/
│   │   └── AppLayout.tsx         # NEW: top bar + <Outlet/> + bottom tab bar (mobile)
│   └── ui/
│       ├── Card.tsx              # NEW
│       ├── PageHeader.tsx        # NEW
│       ├── Button.tsx            # NEW
│       ├── EmptyState.tsx        # NEW
│       ├── TabStrip.tsx          # NEW
│       └── FormField.tsx         # NEW
├── pages/                        # all 7 rewritten
│   ├── Home.tsx
│   ├── Auth.tsx
│   ├── Crews.tsx
│   ├── CrewDetail.tsx
│   ├── PostSleep.tsx
│   ├── UserProfile.tsx
│   └── Settings.tsx
├── hooks/useAuthSession.ts       # unchanged
├── lib/                          # unchanged
├── api/                          # unchanged
└── __tests__/smoke.test.tsx      # updated per §8
```

Page-specific components stay co-located with their page until a second consumer appears. `components/ui/` is for primitives only; `components/layout/` is for layout shells.

## 8. Testing impact

The existing smoke test (`src/__tests__/smoke.test.tsx`) asserts every route renders at least one `<h1>`. This pass changes two assertions:

1. **`/` no longer renders an `<h1>`** — it's a redirect. We replace the route-h1 assertion for `/` with an explicit redirect assertion: rendering `/` with a logged-out session should land us on the `/auth` page's wordmark.

2. **`/auth` needs an `<h1>`** — the wordmark "synzoia" gets wrapped in `<h1>` so the smoke test stays green and accessibility is preserved.

Updated test sketch:

```tsx
vi.mock('@/lib/supabase', () => ({ /* unchanged */ }));
vi.mock('@/hooks/useAuthSession', () => ({
  useAuthSession: () => ({ session: null, loading: false }),
}));

const routesWithHeading = [
  '/auth',
  '/crews',
  '/crews/abc',
  '/crews/abc/post',
  '/users/xyz',
  '/settings',
];

for (const route of routesWithHeading) {
  it(`renders an <h1> at ${route}`, () => {
    const { container } = renderAt(route);
    expect(container.querySelectorAll('h1').length).toBeGreaterThanOrEqual(1);
  });
}

it('redirects "/" to /auth when logged out', () => {
  const { container } = renderAt('/');
  expect(container.querySelector('h1')?.textContent).toBe('synzoia');
});
```

Test count: 4 existing `apiFetch` + 6 route h1 + 1 redirect = **11 total**, same as before. No new infrastructure.

## 9. Acceptance checks

After this lands:

1. `npm run typecheck`, `npm run lint`, `npm run test` (11 tests) all exit 0.
2. `npm run build` produces `dist/`.
3. In the dev server, every route renders with `AppLayout` chrome (top bar visible, bottom tab bar visible on mobile widths).
4. `/auth` shows the centered-card layout with no nav chrome.
5. Visiting `/` redirects to `/auth` (since `useAuthSession` returns null session).
6. On `/crews/abc`, clicking each tab label updates `?tab=` in the URL and swaps the empty-state message.
7. On `/crews/abc`, clicking "Post sleep" navigates to `/crews/abc/post`.
8. Every disabled button shows `opacity-50 cursor-not-allowed` and does not navigate or submit.
9. Mobile viewport (Chrome devtools, 375px wide): top bar shows wordmark only (no Settings link), bottom tab bar visible, main content has `pb-24` clearance so nothing hides behind the bar.
10. Desktop viewport (≥ 640px): top bar shows wordmark + Settings link, bottom tab bar hidden.
