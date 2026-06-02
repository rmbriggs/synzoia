# Congratulatory Leaderboard Recap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the daily leaderboard recap card celebratory — a "Congrats to the top 3" heading and 🥇🥈🥉 medals instead of `#1/#2/#3`.

**Architecture:** A single presentational change in `RecapPost.tsx` (the feed builds the recap card from `details.top`; no backend involved). Medals carry an accessible per-rank label.

**Tech Stack:** React, Vitest + React Testing Library.

---

## Setup

- [ ] **Step 0: Confirm deps reachable**

Run:
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default/frontend
ls node_modules/.bin/vitest
```
Expected: path prints (symlink already in place from earlier work).

---

### Task 1: Congratulatory heading + medal podium

**Files:**
- Modify: `frontend/src/components/feed/RecapPost.tsx`
- Test: `frontend/src/__tests__/Feed.test.tsx`

- [ ] **Step 1: Update + add the failing tests**

In `frontend/src/__tests__/Feed.test.tsx`, in the test `renders a recap card with the top-3 list`, replace:
```ts
    await waitFor(() => {
      expect(screen.getByText('Top 3 · May 23, 2026')).toBeInTheDocument();
    });
```
with:
```ts
    await waitFor(() => {
      expect(
        screen.getByText(/Congrats to the top 3 · May 23, 2026/),
      ).toBeInTheDocument();
    });
    expect(screen.getByText('🥇')).toBeInTheDocument();
    expect(screen.getByText('🥈')).toBeInTheDocument();
    expect(screen.getByText('🥉')).toBeInTheDocument();
    expect(screen.queryByText('#1')).not.toBeInTheDocument();
```

In the test `renders milestone + recap together in a mixed feed`, replace:
```ts
    expect(screen.getByText('Top 3 · May 23, 2026')).toBeInTheDocument();
```
with:
```ts
    expect(
      screen.getByText(/Congrats to the top 3 · May 23, 2026/),
    ).toBeInTheDocument();
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
npm test -- --run src/__tests__/Feed.test.tsx
```
Expected: FAIL — the heading is still "Top 3 · …" (no "Congrats"), and there are no 🥇/🥈/🥉 (still `#1/#2/#3`).

- [ ] **Step 3: Update RecapPost**

In `frontend/src/components/feed/RecapPost.tsx`:

(a) Replace the heading derivation and `<h3>` (currently):
```tsx
  const rankedDate = post.details?.date;
  const heading = rankedDate ? `Top 3 · ${formatDateMedium(rankedDate)}` : 'Top 3';
```
with:
```tsx
  const rankedDate = post.details?.date;
  const heading = rankedDate
    ? `Congrats to the top 3 · ${formatDateMedium(rankedDate)}`
    : 'Congrats to the top 3';
```

(b) Replace the heading element (currently):
```tsx
        <h3 className="font-display text-xl tracking-tight">{heading}</h3>
```
with:
```tsx
        <h3 className="font-display text-xl tracking-tight">
          <span aria-hidden="true">🏆 </span>
          {heading}
        </h3>
```

(c) Add the medal constants just above the `return` (after the `heading` line):
```tsx
  const medals = ['🥇', '🥈', '🥉'];
  const places = ['1st place', '2nd place', '3rd place'];
```

(d) Replace the rank-label span inside the `top.map(...)` (currently):
```tsx
            <span className="label-mono w-6 shrink-0 text-muted-foreground">
              #{i + 1}
            </span>
```
with:
```tsx
            <span
              role="img"
              aria-label={places[i] ?? `${i + 1}th place`}
              className="w-6 shrink-0 text-center"
            >
              {medals[i] ?? `#${i + 1}`}
            </span>
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
npm test -- --run src/__tests__/Feed.test.tsx
```
Expected: PASS — new heading present, 🥇/🥈/🥉 render, `#1` gone, all other Feed tests still pass.

- [ ] **Step 5: Full check (suite + typecheck + lint)**

Run:
```bash
npm test -- --run && npm run typecheck && npx eslint src/components/feed/RecapPost.tsx
```
Expected: all tests pass, typecheck clean, eslint exits 0 for RecapPost.tsx.

- [ ] **Step 6: Commit**

```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/feed-as-default
git add frontend/src/components/feed/RecapPost.tsx frontend/src/__tests__/Feed.test.tsx
git commit -m "feat(feed): celebratory recap — 'Congrats to the top 3' + medal podium

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:** celebratory heading with decorative 🏆 + date format (Step 3a/3b); medal podium with per-rank `aria-label` + defensive fallback (Step 3c/3d); no-date heading fallback (Step 3a `: 'Congrats to the top 3'`); tests updated + medal assertions (Step 1). All spec sections covered. ✓
- **Placeholder scan:** none — every step has complete code and exact commands.
- **Type consistency:** `medals`/`places` are local `string[]`; `heading` stays a `string`; `formatDateMedium` already imported in RecapPost (from the feed-clarity change). The `places[i] ?? ...` and `medals[i] ?? ...` fallbacks are safe for any `i`.
