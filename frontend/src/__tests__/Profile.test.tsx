import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Profile from '@/pages/Profile';

function renderAt(username: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/u/${username}`]}>
        <Routes>
          <Route path="/u/:username" element={<Profile />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.clearAllMocks();
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

describe('Profile page', () => {
  it('renders summary stats, weekly bars, and today card for a known user', async () => {
    globalThis.fetch = routedMock({
      '/summary': () =>
        ok({
          username: 'alice',
          join_date: '2026-05-01T00:00:00Z',
          total_steps_all_time: 50000,
          best_day: { date: '2026-05-20', total: 12000 },
          rank_all_time: 1,
          days_active: 5,
        }),
      '/weekly': () =>
        ok({
          username: 'alice',
          week_start: '2026-05-18',
          week_end: '2026-05-24',
          weekly_total: 30000,
          rank_this_week: 1,
          daily_breakdown: Array.from({ length: 7 }).map((_, i) => ({
            date: `2026-05-${String(18 + i).padStart(2, '0')}`,
            total: (i + 1) * 1000,
          })),
        }),
      '/daily': () =>
        ok({
          username: 'alice',
          date: '2026-05-23',
          total: 8000,
          rank_today: 2,
          posts: [
            { timestamp: '2026-05-23T08:00:00', total: 3000 },
            { timestamp: '2026-05-23T14:00:00', total: 8000 },
          ],
        }),
    });

    renderAt('alice');

    // Wait for a value that only appears once all three queries resolve.
    expect(await screen.findByText('50,000')).toBeInTheDocument(); // all-time
    expect(screen.getByRole('heading', { level: 1, name: 'alice' })).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument(); // days active
    expect(screen.getByText('#1')).toBeInTheDocument(); // all-time rank
    expect(screen.getByText('12,000')).toBeInTheDocument(); // best day
    expect(await screen.findByText('This week')).toBeInTheDocument();
    expect(await screen.findByText('Today')).toBeInTheDocument();
    expect(screen.getByText('8,000')).toBeInTheDocument(); // today total
    expect(screen.getByText('2 snapshots')).toBeInTheDocument();
  });

  it('renders the not-found view when the API returns user_not_found', async () => {
    globalThis.fetch = routedMock({ '/users/': () => notFound() });

    renderAt('nobody');

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { level: 1, name: /No one named nobody/ }),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole('link', { name: 'Back to feed' }),
    ).toBeInTheDocument();
  });

  it('shows fallback symbols when rank/best-day are missing', async () => {
    globalThis.fetch = routedMock({
      '/summary': () =>
        ok({
          username: 'lonely',
          join_date: '2026-05-23T00:00:00Z',
          total_steps_all_time: 0,
          best_day: null,
          rank_all_time: null,
          days_active: 0,
        }),
      '/weekly': () =>
        ok({
          username: 'lonely',
          week_start: '2026-05-18',
          week_end: '2026-05-24',
          weekly_total: 0,
          rank_this_week: null,
          daily_breakdown: Array.from({ length: 7 }).map((_, i) => ({
            date: `2026-05-${String(18 + i).padStart(2, '0')}`,
            total: 0,
          })),
        }),
      '/daily': () =>
        ok({
          username: 'lonely',
          date: '2026-05-23',
          total: 0,
          rank_today: null,
          posts: [],
        }),
    });

    renderAt('lonely');

    // Wait for the today-card empty message — appears only after the
    // daily query resolves, which is the last of the three to render.
    expect(
      await screen.findByText('No posts yet today.'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 1, name: 'lonely' }),
    ).toBeInTheDocument();
    // Rank-all-time + best-day both show "—" when null.
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });
});
