import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Leaderboard from '@/pages/Leaderboard';

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Leaderboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.clearAllMocks();
});

function mockOnce(url: RegExp, payload: unknown, status = 200) {
  return vi.fn().mockImplementation((input: string) => {
    if (url.test(input)) {
      return Promise.resolve(
        new Response(JSON.stringify(payload), {
          status,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    }
    return Promise.resolve(new Response('{}', { status: 200 }));
  });
}

describe('Leaderboard page', () => {
  it('defaults to the Today board and keeps both tabs', async () => {
    const payload = {
      date: '2026-06-03',
      total_steps: 21000,
      participating_users: 2,
      leaderboard: [
        { rank: 1, username: 'alice', total: 12000 },
        { rank: 2, username: 'bob', total: 9000 },
      ],
    };
    globalThis.fetch = mockOnce(/\/steps\/daily/, payload);

    // No ?tab param → the page now defaults to Today, so the daily board loads.
    renderAt('/leaderboard');

    await waitFor(() => {
      expect(screen.getByText('@alice')).toBeInTheDocument();
    });
    expect(screen.getByText('21,000 total steps')).toBeInTheDocument();
    // Both tabs remain available.
    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('Last 30 days')).toBeInTheDocument();
  });

  it('renders the 30-day leaderboard when ?tab=ranking', async () => {
    const payload = {
      week_start: '2026-05-04',
      week_end: '2026-06-03',
      total_steps: 50000,
      leaderboard: [
        { rank: 1, username: 'alice', total: 30000 },
        { rank: 2, username: 'bob', total: 20000 },
      ],
      daily_breakdown: [],
    };
    globalThis.fetch = mockOnce(/\/steps\/ranking/, payload);

    renderAt('/leaderboard?tab=ranking');

    await waitFor(() => {
      expect(screen.getByText('@alice')).toBeInTheDocument();
    });
    expect(screen.getByText('@bob')).toBeInTheDocument();
    expect(screen.getByText('30,000')).toBeInTheDocument();
    expect(screen.getByText('20,000')).toBeInTheDocument();
    expect(screen.getByText('50,000 total steps')).toBeInTheDocument();
  });

  it('renders the daily leaderboard when ?tab=today', async () => {
    const payload = {
      date: '2026-05-23',
      total_steps: 21000,
      participating_users: 2,
      leaderboard: [
        { rank: 1, username: 'bob', total: 12000 },
        { rank: 2, username: 'alice', total: 9000 },
      ],
    };
    globalThis.fetch = mockOnce(/\/steps\/daily/, payload);

    renderAt('/leaderboard?tab=today');

    await waitFor(() => {
      expect(screen.getByText('@bob')).toBeInTheDocument();
    });
    expect(screen.getByText('@alice')).toBeInTheDocument();
    expect(screen.getByText('12,000')).toBeInTheDocument();
    expect(screen.getByText('21,000 total steps')).toBeInTheDocument();
  });

  it('shows the empty state when no one has posted in the last 30 days', async () => {
    const payload = {
      week_start: '2026-05-04',
      week_end: '2026-06-03',
      total_steps: 0,
      leaderboard: [],
      daily_breakdown: [],
    };
    globalThis.fetch = mockOnce(/\/steps\/ranking/, payload);

    renderAt('/leaderboard?tab=ranking');

    await waitFor(() => {
      expect(
        screen.getByText('No one has posted in the last 30 days.'),
      ).toBeInTheDocument();
    });
  });

  it('shows an error card with a retry button when the ranking request fails', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(new Response('boom', { status: 500 }));

    renderAt('/leaderboard');

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Try again' }),
      ).toBeInTheDocument();
    });
  });

  it('labels the ranking tab "Last 30 days"', async () => {
    const payload = {
      date: '2026-06-03',
      total_steps: 9000,
      participating_users: 1,
      leaderboard: [{ rank: 1, username: 'alice', total: 9000 }],
    };
    globalThis.fetch = mockOnce(/\/steps\/daily/, payload);

    renderAt('/leaderboard');

    // The 30-day tab is always labelled, even though Today is the active board.
    expect(await screen.findByText('Last 30 days')).toBeInTheDocument();
    expect(screen.queryByText('Last 7 days')).not.toBeInTheDocument();
    expect(screen.queryByText('This Week')).not.toBeInTheDocument();
  });

  it('links each leaderboard row to /u/:username', async () => {
    const payload = {
      week_start: '2026-05-04',
      week_end: '2026-06-03',
      total_steps: 9000,
      leaderboard: [{ rank: 1, username: 'alice', total: 9000 }],
      daily_breakdown: [],
    };
    globalThis.fetch = mockOnce(/\/steps\/ranking/, payload);

    renderAt('/leaderboard?tab=ranking');

    await waitFor(() => {
      const link = screen.getByRole('link', { name: '@alice' });
      expect(link).toHaveAttribute('href', '/u/alice');
    });
  });
});
