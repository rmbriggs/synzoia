import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Feed from '@/pages/Feed';

function renderFeed() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/feed']}>
        <Feed />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.clearAllMocks();
});

describe('Feed page', () => {
  it('renders the leaderboard and totals after a successful fetch', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          date: '2026-05-23',
          total_steps: 21000,
          participating_users: 2,
          leaderboard: [
            { rank: 1, username: 'bob', total: 12000 },
            { rank: 2, username: 'alice', total: 9000 },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText('21,000')).toBeInTheDocument();
    });
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('12,000')).toBeInTheDocument();
    expect(screen.getByText('9,000')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('#2')).toBeInTheDocument();
  });

  it('shows the empty state when no one has posted today', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          date: '2026-05-23',
          total_steps: 0,
          participating_users: 0,
          leaderboard: [],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    renderFeed();

    await waitFor(() => {
      expect(
        screen.getByText('No one has posted yet today.'),
      ).toBeInTheDocument();
    });
  });

  it('shows an error card with a retry button when the request fails', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response('boom', { status: 500 }),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    });
  });

  it('links each leaderboard row to /u/:username', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          date: '2026-05-23',
          total_steps: 9000,
          participating_users: 1,
          leaderboard: [{ rank: 1, username: 'alice', total: 9000 }],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    renderFeed();

    await waitFor(() => {
      const link = screen.getByRole('link', { name: 'alice' });
      expect(link).toHaveAttribute('href', '/u/alice');
    });
  });

  it('calls the daily endpoint with no date param so the server defaults to today', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          date: '2026-05-23',
          total_steps: 0,
          participating_users: 0,
          leaderboard: [],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    globalThis.fetch = fetchMock;

    renderFeed();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    const url = fetchMock.mock.calls[0][0] as string;
    // The frontend passes the user's local YYYY-MM-DD as ?date= so
    // that the user's "Today" matches their wall clock, not UTC.
    // See lib/dates.localDate().
    expect(url).toMatch(/\/steps\/daily\?date=\d{4}-\d{2}-\d{2}$/);
  });
});

beforeEach(() => {
  // Quiet the React Query devtools console noise in CI.
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
