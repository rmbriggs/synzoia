# Clearer Feed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the feed easier to scan — group posts under day headers, give each post type a distinct icon/label, clean up body-less post fallbacks, and fix the misleading recap heading.

**Architecture:** A pure `groupPostsByDay` helper + a `formatDayHeader`/`ctDayKey` pair in `lib/dates` provide the day-grouping; `Feed.tsx` renders one section per day group. A shared `POST_TYPE_META` map + `PostTypeIcon` component give the per-type icon (with an accessible label) used by the three one-line post components. `RecapPost` derives its heading from `details.date`.

**Tech Stack:** React + react-router-dom, lucide-react (already a dep), Vitest + React Testing Library.

---

## Setup (worktree)

- [ ] **Step 0: Confirm deps reachable**

This worktree already has a `node_modules` symlink from the earlier change. Verify:
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default/frontend
ls node_modules/.bin/vitest
```
Expected: path prints. If missing, run `ln -s /Users/micahbriggs/Developer/synzoia/frontend/node_modules ./node_modules`.

All test/typecheck commands below run from that `frontend/` directory.

---

### Task 1: `ctDayKey` + `formatDayHeader` date helpers

**Files:**
- Modify: `frontend/src/lib/dates.ts`
- Test: `frontend/src/lib/__tests__/dates.test.ts`

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/lib/__tests__/dates.test.ts` (and add the imports `ctDayKey, formatDayHeader` to the existing top import from `@/lib/dates`):

```ts
describe('ctDayKey', () => {
  it('returns the CT calendar day (YYYY-MM-DD) of a UTC timestamp', () => {
    expect(ctDayKey('2026-05-27T15:00:00Z')).toBe('2026-05-27');
  });
});

describe('formatDayHeader', () => {
  const now = new Date('2026-05-29T18:00:00Z'); // ~1pm CT, 2026-05-29

  it('labels the current CT day "Today"', () => {
    expect(formatDayHeader('2026-05-29T18:00:00Z', now)).toBe('Today');
  });

  it('labels the prior CT day "Yesterday"', () => {
    expect(formatDayHeader('2026-05-28T18:00:00Z', now)).toBe('Yesterday');
  });

  it('labels older days as "Weekday, Month Day"', () => {
    expect(formatDayHeader('2026-05-27T15:00:00Z', now)).toBe('Wednesday, May 27');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
npm test -- --run src/lib/__tests__/dates.test.ts
```
Expected: FAIL — `ctDayKey`/`formatDayHeader` are not exported (import error / not a function).

- [ ] **Step 3: Implement the helpers**

In `frontend/src/lib/dates.ts`, add these exports (place them just after the `parseAsUtc` function so they can use `parseAsUtc`, `CT_YMD`, and `APP_TIMEZONE`):

```ts
/**
 * The CT calendar day (YYYY-MM-DD) a timestamp falls on. Used to group
 * feed posts by day. Robust against naive-UTC strings (see parseAsUtc).
 */
export function ctDayKey(iso: string): string {
  return CT_YMD.format(parseAsUtc(iso));
}

/**
 * A day-group header label for the feed:
 *   today CT     -> "Today"
 *   yesterday CT -> "Yesterday"
 *   older        -> "Wednesday, May 27"
 */
export function formatDayHeader(iso: string, now: Date = new Date()): string {
  const thenKey = ctDayKey(iso);
  const nowKey = CT_YMD.format(now);
  const yesterdayKey = CT_YMD.format(new Date(now.getTime() - 86_400_000));

  if (thenKey === nowKey) return 'Today';
  if (thenKey === yesterdayKey) return 'Yesterday';

  return parseAsUtc(iso).toLocaleDateString('en-US', {
    timeZone: APP_TIMEZONE,
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
npm test -- --run src/lib/__tests__/dates.test.ts
```
Expected: PASS (all dates tests green).

- [ ] **Step 5: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default
git add frontend/src/lib/dates.ts frontend/src/lib/__tests__/dates.test.ts
git commit -m "feat(dates): add ctDayKey + formatDayHeader for feed day grouping

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `groupPostsByDay` helper

**Files:**
- Create: `frontend/src/lib/feedGroups.ts`
- Test: `frontend/src/lib/__tests__/feedGroups.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/__tests__/feedGroups.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { groupPostsByDay } from '@/lib/feedGroups';
import type { FeedPost } from '@/api/posts';

const now = new Date('2026-05-29T18:00:00Z');

function post(id: number, iso: string): FeedPost {
  return {
    id,
    user_id: 1,
    username: 'u',
    type: 'steps',
    timestamp: iso,
    details: null,
    body: null,
  };
}

describe('groupPostsByDay', () => {
  it('splits posts into day groups, newest-first, preserving order', () => {
    const groups = groupPostsByDay(
      [
        post(1, '2026-05-29T20:00:00Z'),
        post(2, '2026-05-29T14:00:00Z'),
        post(3, '2026-05-28T14:00:00Z'),
        post(4, '2026-05-27T14:00:00Z'),
      ],
      now,
    );

    expect(groups.map((g) => g.label)).toEqual([
      'Today',
      'Yesterday',
      'Wednesday, May 27',
    ]);
    expect(groups[0].posts.map((p) => p.id)).toEqual([1, 2]);
    expect(groups[1].posts.map((p) => p.id)).toEqual([3]);
    expect(groups[2].posts.map((p) => p.id)).toEqual([4]);
    expect(groups[0].key).toBe('2026-05-29');
  });

  it('returns a single group when all posts share a day', () => {
    const groups = groupPostsByDay(
      [post(1, '2026-05-29T20:00:00Z'), post(2, '2026-05-29T08:00:00Z')],
      now,
    );
    expect(groups).toHaveLength(1);
    expect(groups[0].posts).toHaveLength(2);
  });

  it('returns [] for an empty feed', () => {
    expect(groupPostsByDay([], now)).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
npm test -- --run src/lib/__tests__/feedGroups.test.ts
```
Expected: FAIL — `@/lib/feedGroups` does not exist (module not found).

- [ ] **Step 3: Implement the helper**

Create `frontend/src/lib/feedGroups.ts`:

```ts
import type { FeedPost } from '@/api/posts';
import { ctDayKey, formatDayHeader } from '@/lib/dates';

export interface DayGroup {
  key: string;
  label: string;
  posts: FeedPost[];
}

/**
 * Split an already-ordered feed into consecutive day groups. The server
 * returns posts newest-first, so groups come out newest-day-first and a
 * single pass (grouping consecutive same-day posts) fully groups them.
 */
export function groupPostsByDay(
  posts: FeedPost[],
  now: Date = new Date(),
): DayGroup[] {
  const groups: DayGroup[] = [];
  for (const post of posts) {
    const key = ctDayKey(post.timestamp);
    const last = groups[groups.length - 1];
    if (last && last.key === key) {
      last.posts.push(post);
    } else {
      groups.push({ key, label: formatDayHeader(post.timestamp, now), posts: [post] });
    }
  }
  return groups;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
npm test -- --run src/lib/__tests__/feedGroups.test.ts
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default
git add frontend/src/lib/feedGroups.ts frontend/src/lib/__tests__/feedGroups.test.ts
git commit -m "feat(feed): add groupPostsByDay helper

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Post-type icons + cleaner generic fallback

**Files:**
- Create: `frontend/src/components/feed/postType.tsx`
- Modify: `frontend/src/components/feed/SleepPost.tsx`
- Modify: `frontend/src/components/feed/MilestonePost.tsx`
- Modify: `frontend/src/components/feed/GenericPost.tsx`
- Test: `frontend/src/__tests__/Feed.test.tsx`

- [ ] **Step 1: Write the failing test**

Add two tests inside the `describe('Feed page (post stream)', ...)` block in `frontend/src/__tests__/Feed.test.tsx`:

```ts
  it('marks a sleep post with an accessible type label', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        posts: [
          {
            id: 3,
            user_id: 1,
            username: 'micah',
            type: 'sleep',
            timestamp: new Date().toISOString(),
            details: { night_of: '2026-05-28', duration_min: 452 },
            body: 'slept 7h 32m',
          },
        ],
      }),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText('slept 7h 32m')).toBeInTheDocument();
    });
    expect(screen.getByRole('img', { name: 'Sleep' })).toBeInTheDocument();
  });

  it('gives a body-less steps post a readable fallback', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        posts: [
          {
            id: 4,
            user_id: 1,
            username: 'micah',
            type: 'steps',
            timestamp: new Date().toISOString(),
            details: null,
            body: null,
          },
        ],
      }),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText('logged steps')).toBeInTheDocument();
    });
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
npm test -- --run src/__tests__/Feed.test.tsx
```
Expected: FAIL — no `img` with name "Sleep" (no icon yet), and the body-less steps post still shows "posted (steps)" not "logged steps".

- [ ] **Step 3: Create the shared type map**

Create `frontend/src/components/feed/postType.tsx`:

```tsx
import { Moon, Trophy, Footprints, Dumbbell, type LucideIcon } from 'lucide-react';
import type { PostType } from '@/api/posts';

interface TypeMeta {
  icon: LucideIcon;
  label: string;
}

/**
 * Per-type icon + human label for feed posts. Only the icon shows; the
 * label is exposed to assistive tech via aria-label (see PostTypeIcon).
 * leaderboard_recap is intentionally absent — RecapPost is its own card.
 */
export const POST_TYPE_META: Partial<Record<PostType, TypeMeta>> = {
  sleep: { icon: Moon, label: 'Sleep' },
  steps_milestone: { icon: Trophy, label: 'Milestone' },
  steps: { icon: Footprints, label: 'Steps' },
  workout: { icon: Dumbbell, label: 'Workout' },
};

export function PostTypeIcon({ type }: { type: PostType }) {
  const meta = POST_TYPE_META[type];
  if (!meta) return null;
  const Icon = meta.icon;
  return (
    <Icon
      size={16}
      strokeWidth={1.75}
      role="img"
      aria-label={meta.label}
      className="text-muted-foreground shrink-0"
    />
  );
}
```

- [ ] **Step 4: Wire the icon into SleepPost**

Replace the contents of `frontend/src/components/feed/SleepPost.tsx` with:

```tsx
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';
import { PostTypeIcon } from '@/components/feed/postType';

export default function SleepPost({ post }: { post: FeedPost }) {
  return (
    <Card>
      <div className="flex items-center gap-3">
        <PostTypeIcon type={post.type} />
        <Link
          to={`/u/${encodeURIComponent(post.username)}`}
          className="font-medium hover:text-primary transition-colors"
        >
          @{post.username}
        </Link>
        <span className="text-muted-foreground">
          {post.body ?? 'logged sleep'}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}
```

- [ ] **Step 5: Wire the icon into MilestonePost**

Replace the contents of `frontend/src/components/feed/MilestonePost.tsx` with:

```tsx
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';
import { PostTypeIcon } from '@/components/feed/postType';

export default function MilestonePost({ post }: { post: FeedPost }) {
  return (
    <Card>
      <div className="flex items-center gap-3">
        <PostTypeIcon type={post.type} />
        <Link
          to={`/u/${encodeURIComponent(post.username)}`}
          className="font-medium hover:text-primary transition-colors"
        >
          @{post.username}
        </Link>
        <span className="text-muted-foreground">
          {post.body ?? 'hit a milestone'}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}
```

- [ ] **Step 6: Wire the icon + fallback into GenericPost**

Replace the contents of `frontend/src/components/feed/GenericPost.tsx` with:

```tsx
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost, PostType } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';
import { PostTypeIcon } from '@/components/feed/postType';

function fallbackText(type: PostType): string {
  if (type === 'steps') return 'logged steps';
  if (type === 'workout') return 'logged a workout';
  return 'posted';
}

export default function GenericPost({ post }: { post: FeedPost }) {
  return (
    <Card>
      <div className="flex items-center gap-3">
        <PostTypeIcon type={post.type} />
        <Link
          to={`/u/${encodeURIComponent(post.username)}`}
          className="font-medium hover:text-primary transition-colors"
        >
          @{post.username}
        </Link>
        <span className="text-muted-foreground">
          {post.body ?? fallbackText(post.type)}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}
```

- [ ] **Step 7: Run test to verify it passes**

Run:
```bash
npm test -- --run src/__tests__/Feed.test.tsx
```
Expected: PASS — the new sleep/steps tests pass and all existing Feed tests still pass (milestone/recap tests unaffected by adding an icon).

- [ ] **Step 8: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default
git add frontend/src/components/feed/postType.tsx frontend/src/components/feed/SleepPost.tsx frontend/src/components/feed/MilestonePost.tsx frontend/src/components/feed/GenericPost.tsx frontend/src/__tests__/Feed.test.tsx
git commit -m "feat(feed): per-type icons + readable fallback for body-less posts

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Accurate recap heading

**Files:**
- Modify: `frontend/src/components/feed/RecapPost.tsx`
- Test: `frontend/src/__tests__/Feed.test.tsx` (update the two tests that assert `/Yesterday/i`)

- [ ] **Step 1: Update the existing tests to the new heading**

In `frontend/src/__tests__/Feed.test.tsx`, the recap posts use `details.date: '2026-05-23'`. `formatDateMedium('2026-05-23')` renders `May 23, 2026`.

In the test `renders a recap card with the top-3 list`, replace:
```ts
    await waitFor(() => {
      expect(screen.getByText(/Yesterday/i)).toBeInTheDocument();
    });
```
with:
```ts
    await waitFor(() => {
      expect(screen.getByText('Top 3 · May 23, 2026')).toBeInTheDocument();
    });
```

In the test `renders milestone + recap together in a mixed feed`, replace:
```ts
    expect(screen.getByText(/Yesterday/i)).toBeInTheDocument();
```
with:
```ts
    expect(screen.getByText('Top 3 · May 23, 2026')).toBeInTheDocument();
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
npm test -- --run src/__tests__/Feed.test.tsx
```
Expected: FAIL — RecapPost still renders "Yesterday's top 3", so "Top 3 · May 23, 2026" is not found.

- [ ] **Step 3: Update RecapPost heading**

In `frontend/src/components/feed/RecapPost.tsx`:

(a) Add `formatDateMedium` to the dates import:
```tsx
import { formatPostedAt, formatDateMedium } from '@/lib/dates';
```

(b) Inside the component, derive the heading from `details.date` (add just after `const top = post.details?.top ?? [];`):
```tsx
  const rankedDate = post.details?.date;
  const heading = rankedDate ? `Top 3 · ${formatDateMedium(rankedDate)}` : 'Top 3';
```

(c) Replace the heading element:
```tsx
        <h3 className="font-display text-xl tracking-tight">
          Yesterday&rsquo;s top 3
        </h3>
```
with:
```tsx
        <h3 className="font-display text-xl tracking-tight">{heading}</h3>
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
npm test -- --run src/__tests__/Feed.test.tsx
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default
git add frontend/src/components/feed/RecapPost.tsx frontend/src/__tests__/Feed.test.tsx
git commit -m "feat(feed): recap heading shows its ranked day, not hardcoded 'Yesterday'

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Render day groups in the feed

**Files:**
- Modify: `frontend/src/pages/Feed.tsx`
- Test: `frontend/src/__tests__/Feed.test.tsx`

- [ ] **Step 1: Write the failing test**

Add this test inside the `describe('Feed page (post stream)', ...)` block in `frontend/src/__tests__/Feed.test.tsx`:

```ts
  it('groups posts under day headers', async () => {
    const todayIso = new Date().toISOString();
    const olderIso = new Date(Date.now() - 2 * 86_400_000).toISOString();
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        posts: [
          {
            id: 1, user_id: 1, username: 'micah', type: 'steps',
            timestamp: todayIso, details: null, body: null,
          },
          {
            id: 2, user_id: 1, username: 'micah', type: 'steps',
            timestamp: olderIso, details: null, body: null,
          },
        ],
      }),
    );

    const { container } = renderFeed();

    await waitFor(() => {
      expect(screen.getByText('Today')).toBeInTheDocument();
    });
    // One <h2> per day group (PageHeader uses <h1>, RecapPost uses <h3>).
    expect(container.querySelectorAll('h2')).toHaveLength(2);
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
npm test -- --run src/__tests__/Feed.test.tsx
```
Expected: FAIL — the flat feed renders no `<h2>` day headers and no "Today" text.

- [ ] **Step 3: Render groups in Feed.tsx**

In `frontend/src/pages/Feed.tsx`:

(a) Add the import:
```tsx
import { groupPostsByDay } from '@/lib/feedGroups';
```

(b) Replace the success branch (the `<div className="space-y-4">…</div>` block that maps `query.data.posts`) with:
```tsx
        <div className="space-y-8">
          {groupPostsByDay(query.data.posts).map((group) => (
            <section key={group.key} className="space-y-4">
              <div className="flex items-center gap-3">
                <h2 className="label-mono text-muted-foreground">
                  {group.label}
                </h2>
                <div className="h-px flex-1 bg-border/60" />
              </div>
              {group.posts.map((post) => {
                if (post.type === 'leaderboard_recap') {
                  return <RecapPost key={post.id} post={post} />;
                }
                if (post.type === 'steps_milestone') {
                  return <MilestonePost key={post.id} post={post} />;
                }
                if (post.type === 'sleep') {
                  return <SleepPost key={post.id} post={post} />;
                }
                return <GenericPost key={post.id} post={post} />;
              })}
            </section>
          ))}
        </div>
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
npm test -- --run src/__tests__/Feed.test.tsx
```
Expected: PASS — "Today" header renders and there are exactly two `<h2>` headers.

- [ ] **Step 5: Full check (suite + typecheck + lint)**

Run:
```bash
npm test -- --run && npm run typecheck && npx eslint src/pages/Feed.tsx src/lib/dates.ts src/lib/feedGroups.ts src/components/feed/postType.tsx src/components/feed/SleepPost.tsx src/components/feed/MilestonePost.tsx src/components/feed/GenericPost.tsx src/components/feed/RecapPost.tsx
```
Expected: all tests pass, typecheck clean, eslint exits 0 for the changed files.

- [ ] **Step 6: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default
git add frontend/src/pages/Feed.tsx frontend/src/__tests__/Feed.test.tsx
git commit -m "feat(feed): group the post stream under day headers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:**
  - §1 Day delimiters → Task 1 (`ctDayKey`/`formatDayHeader`), Task 2 (`groupPostsByDay`), Task 5 (Feed renders groups). ✓
  - §2 Distinct post types → Task 3 (`POST_TYPE_META`/`PostTypeIcon`, wired into Sleep/Milestone/Generic). ✓
  - §3 Cleaner fallback → Task 3 Step 6 (`fallbackText`). ✓
  - §4 Accurate recap label → Task 4. ✓
  - Testing requirements (feedGroups, formatDayHeader, Feed render, recap label) → Tasks 1, 2, 3, 4, 5. ✓
- **Placeholder scan:** none — every code step has complete code; every run step has an exact command + expected result.
- **Type consistency:** `ctDayKey`/`formatDayHeader` signatures match between dates.ts (Task 1) and feedGroups.ts (Task 2). `PostTypeIcon`/`POST_TYPE_META` names match between postType.tsx (Task 3 Step 3) and its consumers (Steps 4-6). `groupPostsByDay`/`DayGroup` match between Task 2 and Task 5. `fallbackText` defined and used in the same file (Task 3 Step 6). Recap uses existing `formatDateMedium`.
