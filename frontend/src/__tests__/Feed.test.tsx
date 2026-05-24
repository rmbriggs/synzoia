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

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('Feed page (post stream)', () => {
  it('renders milestone posts with username + body + relative time', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        posts: [
          {
            id: 1,
            user_id: 1,
            username: 'micah',
            type: 'steps_milestone',
            timestamp: new Date().toISOString(),
            details: { threshold: 5000, date: '2026-05-23' },
            body: 'hit 5,000 steps',
          },
        ],
      }),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText('hit 5,000 steps')).toBeInTheDocument();
    });
    const link = screen.getByRole('link', { name: '@micah' });
    expect(link).toHaveAttribute('href', '/u/micah');
  });

  it('renders a recap card with the top-3 list', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        posts: [
          {
            id: 7,
            user_id: 1,
            username: 'micah',
            type: 'leaderboard_recap',
            timestamp: new Date().toISOString(),
            details: {
              date: '2026-05-23',
              top: [
                { username: 'micah', total: 12000 },
                { username: 'angela', total: 9500 },
                { username: 'bob', total: 4200 },
              ],
            },
            body: "Yesterday's top 3",
          },
        ],
      }),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText(/Yesterday/i)).toBeInTheDocument();
    });
    expect(screen.getByText('12,000')).toBeInTheDocument();
    expect(screen.getByText('9,500')).toBeInTheDocument();
    expect(screen.getByText('4,200')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: '@angela' }),
    ).toHaveAttribute('href', '/u/angela');
  });

  it('shows the empty state when no posts have been written', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ posts: [] }),
    );

    renderFeed();

    await waitFor(() => {
      expect(
        screen.getByText('No posts yet. Start walking.'),
      ).toBeInTheDocument();
    });
  });

  it('shows an error card with retry on failed fetch', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(new Response('boom', { status: 500 }));

    renderFeed();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Try again' }),
      ).toBeInTheDocument();
    });
  });

  it('renders milestone + recap together in a mixed feed', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        posts: [
          {
            id: 9,
            user_id: 1,
            username: 'micah',
            type: 'leaderboard_recap',
            timestamp: new Date().toISOString(),
            details: {
              date: '2026-05-23',
              top: [{ username: 'micah', total: 9000 }],
            },
            body: "Yesterday's top 3",
          },
          {
            id: 8,
            user_id: 2,
            username: 'angela',
            type: 'steps_milestone',
            timestamp: new Date().toISOString(),
            details: { threshold: 10000, date: '2026-05-23' },
            body: 'hit 10,000 steps',
          },
        ],
      }),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText('hit 10,000 steps')).toBeInTheDocument();
    });
    expect(screen.getByText(/Yesterday/i)).toBeInTheDocument();
  });
});
