# Client-side "current user" + quick profile access

**Date**: 2026-05-26
**Author**: Micah (with Claude Opus 4.7)
**Status**: Proposed
**Builds on**: the users-pages work (Profile page + AppLayout) in PR #38 / branch `worktree-users-pages`.

## 0. Context

synzoia has no login — the website is unauthenticated and the iOS Shortcut carries its own token out-of-band. There's currently no notion of "which user am I" on the website. A visitor can browse every profile at `/u/:username` but has no shortcut back to their own data.

This adds a purely **client-side** notion of "the current user": a person clicks "Make this me" on their own profile, the username is saved in `localStorage`, and a profile icon in the top-right (and the mobile bottom nav) jumps straight to their profile thereafter. No backend changes, no auth, no network calls — just a convenience pointer stored in the browser.

## 1. Locked-in design decisions

| Decision | Choice |
|---|---|
| Persistence | `localStorage`, key `synzoia.currentUser`, value = username string. No backend. |
| Cross-component sync | Custom `window` event `synzoia:currentuser` + native `storage` event. No React Context / provider. |
| Pre-set icon behavior | Icon is always visible. Before a user is claimed it links to `/users`; after, to `/u/<currentUser>`. |
| Button on own saved profile | Disabled "✓ This is you". |
| Button on any other profile | "Make this me" (primary); clicking reassigns the current user. |
| Icon placement | Header top-right (next to ThemeToggle, all screen sizes) AND a "Me" item in the mobile bottom pill. |
| Deleted-user edge case | Stored username that no longer exists → `/u/<name>` already renders `NotFoundView`. Graceful; no special handling. |

## 2. The hook — `frontend/src/hooks/useCurrentUser.ts` (new)

Mirrors the structure of its sibling `useTheme.ts` (feature-detected localStorage helpers), adding cross-component reactivity.

```ts
const STORAGE_KEY = 'synzoia.currentUser';
const SYNC_EVENT = 'synzoia:currentuser';
```

Internal helpers (feature-detected, swallow errors — same shape as `useTheme`):
- `readStored(): string | null` — returns the stored username or `null`.
- `writeStored(username: string)` — persists.
- `clearStored()` — removes the key.

`useCurrentUser()` returns:

```ts
{
  currentUser: string | null;
  setCurrentUser(username: string): void;
  clearCurrentUser(): void;
}
```

Behavior:
- Initializes state from `readStored()`.
- `setCurrentUser(u)`: `writeStored(u)`, set local state, then `window.dispatchEvent(new CustomEvent(SYNC_EVENT))`.
- `clearCurrentUser()`: `clearStored()`, set local state `null`, dispatch `SYNC_EVENT`.
- `useEffect` on mount: subscribe to `SYNC_EVENT` (same-tab) and `storage` (cross-tab); both re-read from `readStored()` and update state. Unsubscribe on unmount.

This makes every hook instance in the tab update the instant any one of them sets the value — which is what keeps the persistent header icon in sync with the button click on the Profile page without a remount.

## 3. "Make this me" button — `frontend/src/pages/Profile.tsx`

Rendered in the `Profile` component just below the `<Header>` element (NOT inside the `Header` component — `Header` stays a dumb presentational component; the button + hook live in `Profile` next to it). Shown on the normal render path only — never on the `NotFoundView` early-return path.

- `const { currentUser, setCurrentUser } = useCurrentUser();`
- If `currentUser === username`:
  - `<Button variant="secondary" disabled>✓ This is you</Button>`
- Else:
  - `<Button variant="primary" onClick={() => setCurrentUser(username)}>Make this me</Button>`

`username` is the route param (already in scope). Uses the existing `AppButton` component — no new button styles.

## 4. Profile icon — `frontend/src/components/layout/AppLayout.tsx`

**Shared destination:** a single computed value so header and pill never diverge:

```tsx
const { currentUser } = useCurrentUser();
const profileTarget = currentUser
  ? `/u/${encodeURIComponent(currentUser)}`
  : '/users';
```

**Header (top-right):** add a `lucide-react` `CircleUser` icon link next to `ThemeToggle`, always visible:

```tsx
<Link to={profileTarget} aria-label="Your profile" className={/* matches ThemeToggle icon-button styling */}>
  <CircleUser size={20} strokeWidth={1.75} />
</Link>
```

**Mobile bottom pill:** add a `BottomNavItem` labeled "Me" with the `CircleUser` icon, pointing at `profileTarget`, placed after the Database item.

Note: `BottomNavItem` uses `NavLink ... end`, which sets active styling on exact-path match. The "Me" target is dynamic (`/users` or `/u/<name>`), so it'll show active styling when the user is on whichever page it currently points to — acceptable and arguably correct.

## 5. Testing

**`frontend/src/hooks/__tests__/useCurrentUser.test.ts` (new):**
- Returns `null` when storage is empty.
- `setCurrentUser('alice')` persists to localStorage and updates the returned value.
- Reads an existing stored value on mount.
- A second component using the hook reflects the update fired via `synzoia:currentuser` (render two hook consumers, set in one, assert the other updates).
- `clearCurrentUser()` resets to `null` and removes the key.

**`frontend/src/__tests__/Profile.test.tsx` (extend):**
- Nothing set → button reads "Make this me".
- Clicking "Make this me" persists the username and the button flips to "✓ This is you" (disabled).
- Profile that is already the saved current user → button starts as "✓ This is you", disabled.

**`frontend/src/__tests__/AppLayout.test.tsx` (new):**
- Profile icon links to `/users` when no current user is set.
- Profile icon links to `/u/<name>` when a current user is set (seed localStorage before render).
- Mobile "Me" pill item has the same destination logic.

**Cleanup:** `afterEach` clears `localStorage` (or at least the `synzoia.currentUser` key) so state never leaks between tests.

## 6. Out of scope

- Any backend persistence or auth (explicitly client-only).
- Editing a profile, or "log out / switch account" UI beyond reassigning via "Make this me".
- Syncing the current user across devices (localStorage is per-browser by design).
- A dedicated `/me` route (the icon resolves to the concrete `/u/<name>` URL instead, so the profile stays bookmarkable).

## 7. Implementation order (single PR, suggested commits)

This is small enough to ship as one or two commits on top of the users-pages branch:
1. `feat(frontend): useCurrentUser hook + "make this me" button` (hook + Profile button + tests).
2. `feat(frontend): profile icon in header + mobile nav` (AppLayout icon/pill + tests).
