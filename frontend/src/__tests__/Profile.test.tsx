import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import Profile from '@/pages/Profile';
import { supabase } from '@/lib/supabase';

/**
 * Helper for the "✓ This is you" assertion. Sets up the global
 * Supabase mock so getSession() returns a session whose
 * user_metadata.username matches `username`. Pre-C2 this was a
 * localStorage flag; post-C2 it has to come from a real auth
 * session (otherwise the impersonation hole opens back up).
 */
function signInAs(username: string): void {
  vi.mocked(supabase.auth.getSession).mockResolvedValue({
    data: {
      session: {
        access_token: 'fake-jwt',
        refresh_token: 'fake-refresh',
        expires_at: 9_999_999_999,
        expires_in: 3600,
        token_type: 'bearer',
        user: {
          id: 'fake-uuid',
          email: `${username}@example.com`,
          user_metadata: { username },
          app_metadata: {},
          aud: 'authenticated',
          created_at: '2026-05-01T00:00:00Z',
        },
      },
    },
  } as Awaited<ReturnType<typeof supabase.auth.getSession>>);
}

function renderAt(url: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/u/:username" element={<Profile />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const originalFetch = globalThis.fetch;

afterEach(() => {
  window.localStorage.clear();
  globalThis.fetch = originalFetch;
  vi.clearAllMocks();
  // `vi.clearAllMocks` resets call history but NOT mock
  // implementations, so any `signInAs(...)` from the previous test
  // would leak its `mockResolvedValue` into the next one. Reset
  // getSession back to the global-stub default (signed-out) so
  // each test starts from a known anonymous state.
  vi.mocked(supabase.auth.getSession).mockResolvedValue({
    data: { session: null },
  } as Awaited<ReturnType<typeof supabase.auth.getSession>>);
});

function routedMock(handlers: Record<string, () => Response>) {
  return vi.fn().mockImplementation((input: string) => {
    for (const [pattern, build] of Object.entries(handlers)) {
      if (input.includes(pattern)) return Promise.resolve(build());
    }
    return Promise.resolve(new Response('{}', { status: 200 }));
  });
}

function ok(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

function notFound(): Response {
  return new Response(
    JSON.stringify({
      error: { code: 'user_not_found', message: "No user named 'nobody'." },
    }),
    { status: 404, headers: { 'Content-Type': 'application/json' } },
  );
}

function aliceSummary() {
  return ok({
    username: 'alice',
    join_date: '2026-05-01T00:00:00Z',
    score: 50000,
    best_day: { date: '2026-05-20', total: 12000 },
    rank: 1,
  });
}

function aliceDaily() {
  return ok({
    username: 'alice',
    date: '2026-05-23',
    total: 8000,
    rank_today: 2,
    posts: [
      { timestamp: '2026-05-23T08:00:00', total: 3000 },
      { timestamp: '2026-05-23T14:00:00', total: 8000 },
    ],
  });
}

function aliceWeekly() {
  return ok({
    username: 'alice',
    week_start: '2026-05-18',
    week_end: '2026-05-24',
    weekly_total: 30000,
    rank_this_week: 1,
    daily_breakdown: Array.from({ length: 7 }).map((_, i) => ({
      date: `2026-05-${String(18 + i).padStart(2, '0')}`,
      total: (i + 1) * 1000,
    })),
  });
}

function aliceMonthly() {
  return ok({
    username: 'alice',
    month_start: '2026-05-01',
    month_end: '2026-05-31',
    monthly_total: 75000,
    rank_this_month: 1,
    daily_breakdown: Array.from({ length: 5 }).map((_, i) => ({
      date: `2026-05-${String(20 + i).padStart(2, '0')}`,
      total: (i + 1) * 1000,
    })),
  });
}

function aliceSleepSummary() {
  return ok({
    username: 'alice',
    join_date: '2026-05-01T00:00:00Z',
    score: 8520,
    best_night: { date: '2026-05-20', total: 512 },
    rank: 2,
  });
}

function aliceSleepDaily() {
  return ok({
    username: 'alice',
    date: '2026-05-23',
    total: 452,
    rank_today: 1,
    post: {
      night_of: '2026-05-22',
      bedtime: '2026-05-22T05:00:00',
      wake_time: '2026-05-23T12:32:00',
      duration_min: 452,
      rem_minutes: null,
      core_minutes: null,
      deep_minutes: null,
      awake_minutes: null,
    },
  });
}

function aliceSleepWeekly() {
  return ok({
    username: 'alice',
    week_start: '2026-05-18',
    week_end: '2026-05-24',
    weekly_total: 2710,
    rank_this_week: 1,
    daily_breakdown: [
      { date: '2026-05-18', total: 452 },
      { date: '2026-05-19', total: 400 },
      { date: '2026-05-20', total: 512 },
      { date: '2026-05-21', total: 0 },
      { date: '2026-05-22', total: 446 },
      { date: '2026-05-23', total: 450 },
      { date: '2026-05-24', total: 450 },
    ],
  });
}

function aliceSleepMonthly() {
  return ok({
    username: 'alice',
    month_start: '2026-05-01',
    month_end: '2026-05-31',
    monthly_total: 8520,
    rank_this_month: 2,
    daily_breakdown: [{ date: '2026-05-20', total: 512 }],
  });
}

function summaryMocks() {
  // Pattern order matters because routedMock uses includes() and
  // returns on first match. Full /sleep/... paths come first so they
  // aren't shadowed by the loose /summary, /daily, ... steps keys.
  return {
    '/sleep/users/alice/summary': aliceSleepSummary,
    '/sleep/users/alice/daily': aliceSleepDaily,
    '/sleep/users/alice/weekly': aliceSleepWeekly,
    '/sleep/users/alice/monthly': aliceSleepMonthly,
    '/summary': aliceSummary,
    '/daily': aliceDaily,
    '/weekly': aliceWeekly,
    '/monthly': aliceMonthly,
  };
}

describe('Profile page', () => {
  it('renders the header from the URL username before queries resolve', () => {
    // Fetch never resolves — every query stays pending.
    globalThis.fetch = vi.fn().mockImplementation(() => new Promise(() => {}));

    renderAt('/u/pending');

    // Header must paint synchronously from useParams, not wait on the
    // summary query.
    expect(
      screen.getByRole('heading', { level: 1, name: 'pending' }),
    ).toBeInTheDocument();
  });

  describe('Summary tab (default)', () => {
    it('renders header, stat strip, today, week, and month cards', async () => {
      globalThis.fetch = routedMock(summaryMocks());

      renderAt('/u/alice');

      // Header
      expect(
        await screen.findByRole('heading', { level: 1, name: 'alice' }),
      ).toBeInTheDocument();
      // StatStrip — 30-day score
      expect(await screen.findByText('50,000')).toBeInTheDocument();
      // 'Today' is steps-only (sleep card says 'Last night'); the
      // week/month headings now appear in both the Steps and Sleep
      // sections.
      expect(await screen.findByText('Today')).toBeInTheDocument();
      expect(await screen.findAllByText('Last 7 days')).toHaveLength(2);
      expect(await screen.findAllByText('Last 30 days')).toHaveLength(2);
    });

    it('renders the 3-card strip: 30-day score, rank, best', async () => {
      globalThis.fetch = routedMock(summaryMocks());
      renderAt('/u/alice');
      expect(await screen.findAllByText('30-day score')).toHaveLength(2); // steps + sleep
      expect(screen.getAllByText('Rank')).toHaveLength(2);
      expect(screen.queryByText('All-time steps')).not.toBeInTheDocument();
      expect(screen.queryByText('Days active')).not.toBeInTheDocument();
      expect(screen.queryByText('All-time sleep')).not.toBeInTheDocument();
      expect(screen.queryByText('Nights logged')).not.toBeInTheDocument();
    });

    it('renders the monthly card with total and rank', async () => {
      globalThis.fetch = routedMock(summaryMocks());

      renderAt('/u/alice');

      // Both Steps and Sleep sections render "Last 30 days" headings.
      expect(await screen.findAllByText('Last 30 days')).toHaveLength(2);
      // Header now shows the average per logged day, not the total:
      // breakdown [1000,2000,3000,4000,5000] over 5 days -> avg 3,000.
      expect(screen.getByText(/avg 3,000 steps · #1/)).toBeInTheDocument();
    });

    it('shows an inline message when the month has no activity yet', async () => {
      globalThis.fetch = routedMock({
        ...summaryMocks(),
        '/monthly': () =>
          ok({
            username: 'alice',
            month_start: '2026-05-01',
            month_end: '2026-05-31',
            monthly_total: 0,
            rank_this_month: null,
            daily_breakdown: [],
          }),
      });

      renderAt('/u/alice');

      expect(
        await screen.findByText(/No activity in the last 30 days yet/i),
      ).toBeInTheDocument();
    });

    it('renders a Sleep section with formatted durations', async () => {
      globalThis.fetch = routedMock(summaryMocks());

      renderAt('/u/alice');

      // Section headings (h2 text)
      expect(await screen.findByText('Sleep')).toBeInTheDocument();
      expect(screen.getByText('Steps')).toBeInTheDocument();
      // Best night rendered as a duration (512 min = 8h 32m). The same
      // duration also appears in the week/month bar hover tooltips, so it
      // legitimately occurs more than once.
      expect((await screen.findAllByText('8h 32m')).length).toBeGreaterThanOrEqual(1);
      // 30-day sleep score in whole hours (8520 min = 142h)
      expect(screen.getByText('142h')).toBeInTheDocument();
      // Sleep daily card uses a distinct heading
      expect(screen.getByText('Last night')).toBeInTheDocument();
    });
  });

  describe('Feed tab', () => {
    it('renders posts that mention the user', async () => {
      globalThis.fetch = routedMock({
        ...summaryMocks(),
        '/posts/users/': () =>
          ok({
            posts: [
              {
                id: 99,
                user_id: 1,
                username: 'alice',
                type: 'steps_milestone',
                timestamp: '2026-05-23T22:00:00',
                details: { threshold: 5000, date: '2026-05-23' },
                body: 'hit 5,000 steps',
              },
            ],
          }),
      });

      renderAt('/u/alice?tab=feed');

      expect(await screen.findByText('hit 5,000 steps')).toBeInTheDocument();
    });

    it('shows the empty state when no posts mention the user', async () => {
      globalThis.fetch = routedMock({
        ...summaryMocks(),
        '/posts/users/': () => ok({ posts: [] }),
      });

      renderAt('/u/alice?tab=feed');

      expect(
        await screen.findByText(/No posts mention this user yet/i),
      ).toBeInTheDocument();
    });

    it('prefetches the feed when the Summary page loads (before the Feed tab is opened)', async () => {
      const fetchMock = routedMock({
        ...summaryMocks(),
        '/posts/users/': () => ok({ posts: [] }),
      });
      globalThis.fetch = fetchMock;

      // Land on the Summary tab — NOT ?tab=feed.
      renderAt('/u/alice');

      // The prefetch effect fetches the feed endpoint even though the
      // Feed tab was never opened. (On the Summary tab nothing else hits
      // /posts/users/* — the stat queries hit /steps/* and /sleep/*.)
      await waitFor(() =>
        expect(
          fetchMock.mock.calls.some(([url]) =>
            String(url).includes('/posts/users/alice'),
          ),
        ).toBe(true),
      );
    });

  });

  describe('Error and fallback states', () => {
    it('renders the not-found view when the API returns user_not_found', async () => {
      globalThis.fetch = routedMock({ '/users/': () => notFound() });

      renderAt('/u/nobody');

      await waitFor(() => {
        expect(
          screen.getByRole('heading', { level: 1, name: /No one named nobody/ }),
        ).toBeInTheDocument();
      });
      expect(
        screen.getByRole('link', { name: 'Back to feed' }),
      ).toBeInTheDocument();
    });

    it('shows fallback dashes for null ranks and missing best-day', async () => {
      globalThis.fetch = routedMock({
        '/sleep/users/lonely/summary': aliceSleepSummary,
        '/sleep/users/lonely/daily': aliceSleepDaily,
        '/sleep/users/lonely/weekly': aliceSleepWeekly,
        '/sleep/users/lonely/monthly': aliceSleepMonthly,
        '/summary': () =>
          ok({
            username: 'lonely',
            join_date: '2026-05-23T00:00:00Z',
            score: 0,
            best_day: null,
            rank: null,
          }),
        '/daily': () =>
          ok({
            username: 'lonely',
            date: '2026-05-23',
            total: 0,
            rank_today: null,
            posts: [],
          }),
        '/weekly': () =>
          ok({
            username: 'lonely',
            week_start: '2026-05-18',
            week_end: '2026-05-24',
            weekly_total: 0,
            rank_this_week: null,
            daily_breakdown: [],
          }),
        '/monthly': () =>
          ok({
            username: 'lonely',
            month_start: '2026-05-01',
            month_end: '2026-05-31',
            monthly_total: 0,
            rank_this_month: null,
            daily_breakdown: [],
          }),
      });

      renderAt('/u/lonely');

      // Wait for the last card (month) to render its empty-state message
      // so all four queries have settled before we count dashes.
      expect(
        await screen.findByText(/No activity in the last 30 days yet/i),
      ).toBeInTheDocument();
      expect(screen.getByText('No posts yet today.')).toBeInTheDocument();
      expect(
        screen.getByRole('heading', { level: 1, name: 'lonely' }),
      ).toBeInTheDocument();
      // Standalone "—" elements: Rank (StatStrip), Best day
      // (StatStrip), Today's rank (TodayCard). The week/month dashes
      // are interleaved with "{n} steps · " text in a single span, so
      // getAllByText doesn't see them as standalone.
      expect(screen.getAllByText('—')).toHaveLength(3);
      // Week and month each render "— · —" — with no logged days there's
      // no average to show, so the value falls back to a dash too.
      expect(screen.getAllByText('— · —')).toHaveLength(2);
    });
  });

  describe('"✓ This is you" badge', () => {
    // Pre-C2 there was a "Make this me" button anyone could click to
    // impersonate a profile via localStorage. C2 removed that — the
    // only way the badge shows now is if the viewer signed in via
    // Supabase Auth as that exact user. Two tests cover the binary:
    // signed-in-as-them → badge visible; not signed in (or signed in
    // as someone else) → no badge at all.

    it('shows the badge when the signed-in user owns this profile', async () => {
      signInAs('alice');
      globalThis.fetch = routedMock(summaryMocks());

      renderAt('/u/alice');

      const badge = await screen.findByRole('button', {
        name: /this is you/i,
      });
      expect(badge).toBeDisabled();
    });

    it('hides the badge when the viewer is not signed in', async () => {
      // Default mock: getSession() resolves to { session: null }.
      // The viewer is anonymous; they should NOT see a "you" badge
      // on someone else's profile.
      globalThis.fetch = routedMock(summaryMocks());

      renderAt('/u/alice');

      // Wait for the page header to render so we know auth has
      // resolved (otherwise we'd race the assertion against the
      // initial loading state).
      await screen.findByRole('heading', { name: /@?alice/i });
      expect(
        screen.queryByRole('button', { name: /this is you/i }),
      ).not.toBeInTheDocument();
    });
  });
});
