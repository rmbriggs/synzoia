# SP3 — Page Redesigns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild all five pages in the coastal language (on the SP2 theme), using only real data, reintroducing Landing as the front door at `/`.

**Architecture:** Frontend-only. A shared `UserAvatar` (deterministic initials + coastal gradient) is built first, then each page is restyled/rebuilt against the existing React Query data hooks and the coastal mockups, omitting any mockup element with no backend. Each page is an independent task that ships to the Vercel preview.

**Tech Stack:** React + TypeScript + Vite, Tailwind v4 + shadcn primitives (from SP2), React Query, react-router-dom, vitest.

## Global Constraints

- **Real data only.** Every element shown is backed by an existing API. Do NOT fabricate metrics. Mockup elements with no backend are OMITTED, not stubbed with fake data. Specifically omit everywhere: heart rate, calories, meals/food, photo attachments/uploads, likes/comments/shares, followers/following, follow/message buttons, badges, weather, trending hashtags, suggested users, online/presence dots.
- **Two allowed no-backend additions:** (1) generated avatars via the new `UserAvatar`; (2) a day streak computed client-side from existing daily-steps data.
- **Frontend only.** No backend, API, Supabase, or new-endpoint changes. No changes to data-hook signatures.
- **Use SP2 primitives + tokens.** Card/AppCard, AppButton, Badge, PageHeader, TabStrip, Input/Label, `UserAvatar`; token-driven classes only, NO hardcoded hex/rgb. Fonts/colors come from the theme.
- **Preserve loading + error + empty states** on every data fetch (skeletons/retry, not blank screens). React Query only (no `useEffect(fetch)`).
- **Routes stay bookmarkable.** Tab selection via URL where it already is.
- **Mockup reference** (read for layout intent; do NOT copy data-less sections): repo `SamM-UATX/synzoia-mockups`, files `landing.html`, `feed.html`, `profile.html`. Local clone at `/Users/micahbriggs/.claude/jobs/0214a46a/tmp/synzoia-mockups/`; if absent, `git clone https://github.com/SamM-UATX/synzoia-mockups` to a temp dir. No mockup exists for Leaderboard or Users — apply the coastal language.
- **Testing note (visual work):** classic unit-TDD fits only the pure helpers (avatar hashing, streak). Page redesigns are verified by: `npm run lint` + `npm run typecheck` + `npx vitest run` (existing tests must still pass) + `npm run build`, plus visual review on the preview (Task 7). Do NOT write assertion-free or brittle snapshot tests for the page JSX.
- `frontend/node_modules` is already installed in this worktree; do NOT reinstall.
- Commit messages end with the `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.

**Available real data (exact hooks/shapes):**
- `getFeed(limit?)` -> `FeedResponse { posts: FeedPost[] }`; `FeedPost { id, user_id, username, type, timestamp, details, body }` (types: generic, milestone, leaderboard_recap, sleep). Realtime INSERT subscription already wired in `Feed.tsx`.
- `getProfiles()` -> `{ profiles: { username, join_date, total_steps_all_time }[] }`.
- `getGlobalSummary()` -> `{ total_users, total_steps_all_time, today_leader, this_week_leader, best_day_ever }` (steps). Sleep analogue via `sleep` summary.
- `getGlobalDaily(date?)`, `getGlobalRanking(asOf?)` -> ranked `{ rank, username, total }[]` + totals (steps). Sleep ranking exists too.
- Per-user (in `api/userSummaryQueries.ts`): `stepsSummaryQuery`, `stepsDailyQuery`, `stepsWeeklyQuery`, `stepsMonthlyQuery`, `sleepSummaryQuery`, `sleepDailyQuery`, `sleepWeeklyQuery`, `sleepMonthlyQuery`, `userFeedQuery`, and the `userSummaryQueries(username, today, asOf)` fan-out.

---

### Task 1: UserAvatar component (shared)

**Files:**
- Create: `frontend/src/components/ui/UserAvatar.tsx`
- Create: `frontend/src/components/ui/__tests__/UserAvatar.test.tsx`

**Interfaces:**
- Produces: `UserAvatar({ username: string, size?: 'default'|'sm'|'lg', className?: string })` (default export + named), plus pure helpers `initials(username)` and `coastalGradientIndex(username)` (named exports) for testing. Consumed by Feed, Profile, Leaderboard, Users.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import UserAvatar, { initials, coastalGradientIndex } from '@/components/ui/UserAvatar';

describe('UserAvatar helpers', () => {
  it('initials: first two alphanumerics, uppercased', () => {
    expect(initials('micah')).toBe('MI');
    expect(initials('a')).toBe('A');
    expect(initials('sierra_walker')).toBe('SI');
    expect(initials('')).toBe('?');
  });
  it('coastalGradientIndex is deterministic and in range', () => {
    const a = coastalGradientIndex('micah');
    const b = coastalGradientIndex('micah');
    expect(a).toBe(b);
    expect(a).toBeGreaterThanOrEqual(0);
    expect(a).toBeLessThan(5);
  });
});

describe('UserAvatar render', () => {
  it('renders the initials fallback for a username', () => {
    render(<UserAvatar username="micah" />);
    expect(screen.getByText('MI')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/components/ui/__tests__/UserAvatar.test.tsx`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement UserAvatar**

Create `frontend/src/components/ui/UserAvatar.tsx`:

```tsx
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

// Deterministic, always-coastal gradient pairs (oklch). Kept on-palette so
// avatars never drift into non-coastal hues.
const COASTAL_GRADIENTS: [string, string][] = [
  ['oklch(0.61 0.11 185)', 'oklch(0.44 0.10 155)'], // teal -> fern
  ['oklch(0.44 0.10 155)', 'oklch(0.68 0.14 66)'],  // fern -> amber
  ['oklch(0.68 0.14 66)', 'oklch(0.41 0.09 42)'],   // amber -> bark
  ['oklch(0.61 0.11 185)', 'oklch(0.68 0.14 66)'],  // teal -> amber
  ['oklch(0.41 0.09 42)', 'oklch(0.44 0.10 155)'],  // bark -> fern
];

function hash(username: string): number {
  let h = 0;
  for (let i = 0; i < username.length; i++) h = (h * 31 + username.charCodeAt(i)) >>> 0;
  return h;
}

export function coastalGradientIndex(username: string): number {
  return hash(username) % COASTAL_GRADIENTS.length;
}

export function initials(username: string): string {
  const clean = username.replace(/[^a-zA-Z0-9]/g, '');
  return (clean.slice(0, 2) || '?').toUpperCase();
}

type Props = {
  username: string;
  size?: 'default' | 'sm' | 'lg';
  className?: string;
};

export function UserAvatar({ username, size = 'default', className }: Props) {
  const [from, to] = COASTAL_GRADIENTS[coastalGradientIndex(username)];
  return (
    <Avatar size={size} className={className}>
      <AvatarFallback
        className={cn('font-medium text-white')}
        style={{ backgroundImage: `linear-gradient(135deg, ${from}, ${to})` }}
      >
        {initials(username)}
      </AvatarFallback>
    </Avatar>
  );
}

export default UserAvatar;
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/components/ui/__tests__/UserAvatar.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Typecheck + commit**

Run: `cd frontend && npm run typecheck` (expect pass).
```bash
git add frontend/src/components/ui/UserAvatar.tsx frontend/src/components/ui/__tests__/UserAvatar.test.tsx
git commit -m "feat(ui): UserAvatar with deterministic coastal gradient + initials

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Landing page redesign + route at `/`

**Files:**
- Modify: `frontend/src/pages/Landing.tsx` (rebuild to coastal marketing layout)
- Modify: `frontend/src/App.tsx` (route `/` -> `<Landing />`)

**Interfaces:**
- Consumes: a React Query call to the steps summary (`getGlobalSummary()`) and the sleep summary for the live hero stats.

- [ ] **Step 1: Route Landing at `/`**

In `frontend/src/App.tsx`: import `Landing` (`import Landing from '@/pages/Landing';`) and replace `<Route path="/" element={<Navigate to="/feed" replace />} />` with `<Route path="/" element={<Landing />} />`. Keep all other routes. Remove the now-unused `Navigate` import only if nothing else uses it.

- [ ] **Step 2: Rebuild Landing.tsx to the coastal marketing layout**

Reference `landing.html` for layout. Build these sections using SP2 primitives + tokens, real data only:
- Sticky marketing nav: serif-italic logo with teal `z` (`syn<span className="text-primary">z</span>oia`), anchor links to the on-page sections, and a primary CTA button (AppButton `to="/feed"`) labeled "Open the feed".
- Hero: coastal headline (serif) + subcopy + a **live stat bar**. Fetch with React Query: `useQuery({ queryKey: ['steps','summary'], queryFn: getGlobalSummary })` and the sleep summary. Show real stats only: walkers (`total_users`), all-time steps (`total_steps_all_time`), this week's leader (`this_week_leader`), best day ever (`best_day_ever`), and one real sleep aggregate. The stat bar MUST have loading (skeleton) and error states.
- Features grid (coastal cards): steps + sleep ingestion via the iOS Shortcut; the universal public feed; the leaderboard; per-user profiles. Real features only.
- "How it works" 3-step: join + get a token; paste it into the iOS Shortcut; your steps + sleep post to the shared feed.
- CTA band (use the `.forest-band` / fern styling from the theme) with an AppButton to `/feed`.
- Coastal footer.
- OMIT: photo strip, testimonials, health-ring demo, app-screen preview band, meal photos.

- [ ] **Step 3: Verify gates**

Run: `cd frontend && npm run lint && npm run typecheck && npx vitest run && npm run build`
Expected: all pass (existing tests green; Landing now routed at `/`).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Landing.tsx frontend/src/App.tsx
git commit -m "feat(landing): coastal marketing front door at / with live stats

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Feed post cards redesign

**Files:**
- Modify: `frontend/src/components/feed/GenericPost.tsx`, `MilestonePost.tsx`, `RecapPost.tsx`, `SleepPost.tsx`
- Modify: `frontend/src/pages/Feed.tsx` (optional desktop mini-leaderboard rail)
- Possibly Modify: `frontend/src/components/feed/postType.tsx` if shared bits live there

**Interfaces:**
- Consumes: `UserAvatar` (Task 1); existing `FeedPost` shape and `getFeed` / realtime already in `Feed.tsx`; `getGlobalDaily` for the optional rail.

- [ ] **Step 1: Redesign the post cards to coastal**

Reference `feed.html` post cards. For each post component, render a coastal card (`surface-glass`/Card) with: `UserAvatar` (username), username linking to `/u/:username`, relative timestamp, the post body, a type accent, and a metric chip drawn ONLY from the post's real `details` (e.g. sleep duration for `sleep`; the leader/top entry for `leaderboard_recap`; milestone threshold for `milestone`). Keep `SleepPost`'s existing test passing. Preserve day grouping + the realtime subscription in `Feed.tsx`. Keep loading skeleton + error + empty states.
- OMIT: photo attachments, like/comment/share/DM controls, search, type filters.

- [ ] **Step 2: (Optional cheap win) desktop mini-leaderboard rail**

In `Feed.tsx`, on `lg+` screens only, add a right rail showing top-3 today from `getGlobalDaily(today)` via React Query (with loading/error states), each row using `UserAvatar` + username + total, linking to profiles. Hidden on mobile. If it complicates the realtime layout, skip it and note that in the report.

- [ ] **Step 3: Verify gates**

Run: `cd frontend && npm run lint && npm run typecheck && npx vitest run && npm run build`
Expected: all pass (including `components/feed/__tests__/SleepPost.test.tsx`).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/feed frontend/src/pages/Feed.tsx
git commit -m "feat(feed): coastal post cards with avatars + real metric chips

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Profile page redesign (+ streak util)

**Files:**
- Modify: `frontend/src/pages/Profile.tsx`
- Create: `frontend/src/lib/streak.ts` + `frontend/src/lib/__tests__/streak.test.ts`

**Interfaces:**
- Consumes: `UserAvatar` (Task 1); the existing 8 `userSummaryQueries` hooks (steps/sleep summary/daily/weekly/monthly) + `userFeedQuery`.
- Produces: `currentStreak(days: { date: string; total: number }[], today: string): number`.

- [ ] **Step 1: Write the streak util test**

```ts
import { describe, it, expect } from 'vitest';
import { currentStreak } from '@/lib/streak';

describe('currentStreak', () => {
  it('counts consecutive days ending today with steps > 0', () => {
    const days = [
      { date: '2026-06-16', total: 8000 },
      { date: '2026-06-17', total: 12000 },
      { date: '2026-06-18', total: 9000 },
    ];
    expect(currentStreak(days, '2026-06-18')).toBe(3);
  });
  it('breaks on a zero or missing day', () => {
    const days = [
      { date: '2026-06-16', total: 8000 },
      { date: '2026-06-17', total: 0 },
      { date: '2026-06-18', total: 9000 },
    ];
    expect(currentStreak(days, '2026-06-18')).toBe(1);
  });
  it('is 0 when today has no steps', () => {
    expect(currentStreak([{ date: '2026-06-17', total: 8000 }], '2026-06-18')).toBe(0);
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run src/lib/__tests__/streak.test.ts`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement the streak util**

Create `frontend/src/lib/streak.ts`:

```ts
// Consecutive days ending at `today` (YYYY-MM-DD) with a recorded total > 0.
// `days` need not be sorted. Walks backwards one calendar day at a time.
export function currentStreak(
  days: { date: string; total: number }[],
  today: string,
): number {
  const byDate = new Map(days.map((d) => [d.date, d.total]));
  let streak = 0;
  const cursor = new Date(`${today}T00:00:00Z`);
  for (;;) {
    const key = cursor.toISOString().slice(0, 10);
    const total = byDate.get(key);
    if (total === undefined || total <= 0) break;
    streak += 1;
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return streak;
}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd frontend && npx vitest run src/lib/__tests__/streak.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Rebuild Profile.tsx to coastal**

Reference `profile.html`. Restyle into coastal cards, real data only:
- Header: `UserAvatar` (size `lg`) over a coastal gradient banner (a token-driven gradient block, no photo), `@username` (serif), join date, all-time steps, and the streak (map the steps-daily query data into `{date,total}[]` and call `currentStreak`).
- Stats row: real values only — 30-day step score + rank, 30-day sleep score + rank, best day, best night, all-time steps.
- Body: keep the existing Summary tab (steps + sleep cards + `RangeTrendCard` charts) and the user-posts Feed tab (reuses Task 3's cards), restyled into coastal cards. Steps + sleep may be shown as two ring/gauge visuals (only those two metrics). Keep `?tab=` URL state, loading/error/empty states.
- OMIT: HR/calorie rings, Follow/Message, followers/following, photo grid, badges, online dot.

- [ ] **Step 6: Verify gates**

Run: `cd frontend && npm run lint && npm run typecheck && npx vitest run && npm run build`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Profile.tsx frontend/src/lib/streak.ts frontend/src/lib/__tests__/streak.test.ts
git commit -m "feat(profile): coastal profile with avatar, banner, streak, real stats

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Leaderboard redesign

**Files:**
- Modify: `frontend/src/pages/Leaderboard.tsx`

**Interfaces:**
- Consumes: `UserAvatar` (Task 1); existing `getGlobalDaily`, `getGlobalRanking` (steps) and the sleep ranking hook for the optional tab.

- [ ] **Step 1: Restyle to coastal + medals + avatars**

No mockup; apply the coastal language. Keep the Today / Last-30-days tabs and their data. Render each ranked row as a coastal row/card with `UserAvatar` + `@username` (link to profile) + total, and **top-3 medal coloring** (rank 1 gold, 2 silver, 3 bronze) using token-driven accents. Keep `?tab=` URL state + loading/error/empty states.

- [ ] **Step 2: (Optional cheap win) sleep leaderboard tab**

Add a third tab "Sleep" using the existing sleep ranking endpoint (same row layout). If the sleep ranking hook/shape differs from steps in a way that complicates this, skip and note it in the report.

- [ ] **Step 3: Verify gates**

Run: `cd frontend && npm run lint && npm run typecheck && npx vitest run && npm run build`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Leaderboard.tsx
git commit -m "feat(leaderboard): coastal rows with medals + avatars

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Users redesign

**Files:**
- Modify: `frontend/src/pages/Users.tsx`

**Interfaces:**
- Consumes: `UserAvatar` (Task 1); existing `getProfiles()` (`{ username, join_date, total_steps_all_time }`).

- [ ] **Step 1: Restyle to coastal + show real steps total**

No mockup; apply the coastal language. Render each user row as a coastal row with `UserAvatar` + `@username` (link to profile) + `total_steps_all_time` (already in the response, currently not displayed). Keep the existing hover/focus prefetch behavior and loading/error/empty states.

- [ ] **Step 2: Verify gates**

Run: `cd frontend && npm run lint && npm run typecheck && npx vitest run && npm run build`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Users.tsx
git commit -m "feat(users): coastal user rows with avatars + all-time steps

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Full verification + preview deploy

**Files:** none (gates + PR).

- [ ] **Step 1: Run every gate locally**

Run: `cd frontend && npm run lint && npm run typecheck && npx vitest run && npm run build`
Expected: all pass. Fix anything that fails before proceeding.

- [ ] **Step 2: Push the branch + open a PR (base = SP2 branch)**

The SP3 branch stacks on SP2. Open the PR against the SP2 branch so the diff is SP3-only:
```bash
git push -u origin worktree-sp3-page-redesigns
gh pr create --repo rmbriggs/synzoia --base worktree-sp2-coastal-theme --head worktree-sp3-page-redesigns \
  --title "feat: SP3 page redesigns (coastal, real-data-only)" \
  --body "Landing front door at /, coastal Feed/Profile/Leaderboard/Users with UserAvatar, real data only. Stacks on SP2."
```
(If SP2 has already been merged to `main` by the time this runs, use `--base main` instead.)

- [ ] **Step 3: Watch CI**

Run: `gh pr checks --repo rmbriggs/synzoia worktree-sp3-page-redesigns --watch`
Expected: `backend` + `frontend` checks pass.

- [ ] **Step 4: Get the preview URL + verify each route**

Find the branch preview (Vercel bot comment or `vercel ls synzoia`). Confirm 200 on `/` (Landing), `/feed`, `/leaderboard`, `/users`, and a `/u/:username` for a real user (use one returned by `/api/profiles`, e.g. `micah`). Report the preview URL.

- [ ] **Step 5: Stop for review**

Do NOT merge. Report CI status, the preview URL, and a per-page note. Await go-ahead.

---

## Self-Review

**Spec coverage:**
- Real-data-only principle + omissions list -> Global Constraints; enforced per page. ✓
- Generated avatars -> Task 1 (UserAvatar), used in Tasks 3-6. ✓
- Day streak -> Task 4 (streak util + test, used in Profile). ✓
- Landing front door at `/` -> Task 2 (route + redesign + live stats). ✓
- Feed coastal cards -> Task 3. ✓
- Profile coastal -> Task 4. ✓
- Leaderboard coastal + medals + optional sleep tab -> Task 5. ✓
- Users coastal + all-time steps -> Task 6. ✓
- Frontend-only, preserve loading/error/empty, React Query -> Global Constraints. ✓
- Verification + preview -> per-task gates + Task 7. ✓

**Placeholder scan:** UserAvatar, streak util, routing change, and all tests are concrete code. Page tasks give exact sections to build/omit, exact data hooks, and the mockup reference; full page JSX is intentionally composed by the implementer against the real components + mockup (stated in the Testing note), not transcribed here. No TBD/TODO.

**Type consistency:** `UserAvatar` / `initials` / `coastalGradientIndex` names consistent across Task 1 and its consumers (3-6). `currentStreak(days, today)` signature consistent between Task 4 test and impl and its Profile use. Data hook names match the `Available real data` block. Branch name `worktree-sp3-page-redesigns` consistent (Task 7).

## Notes / Open Risks

- **Optional cheap wins** (Feed mini-leaderboard rail, Leaderboard sleep tab) are explicitly skippable if they complicate the page; the implementer must NOTE a skip in the report (no silent drop).
- **Streak timezone:** the util walks UTC calendar days for testability; the app anchors days to `America/Chicago`. Acceptable for a derived display stat; if the daily-steps `date` values are already CT-anchored strings, the comparison stays consistent.
- **Mockup availability:** primary path is the local clone; fallback is cloning the public mockups repo. Implementers reference layout only and must not import data-less sections.
- **PR base:** SP3 PR targets the SP2 branch so its diff is SP3-only; if SP2 is merged first, retarget to `main`.
