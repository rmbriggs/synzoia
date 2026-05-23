import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Join from '@/pages/Join';

function renderJoin() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/join']}>
        <Join />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function fillAndSubmit(username: string) {
  fireEvent.change(screen.getByLabelText('Username'), {
    target: { value: username },
  });
  fireEvent.click(screen.getByRole('button', { name: /^Join$/ }));
}

const originalFetch = globalThis.fetch;

beforeEach(() => {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
    writable: true,
    configurable: true,
  });
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.clearAllMocks();
});

describe('Join page', () => {
  it('shows the token after a successful sign-up', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          username: 'micah',
          token: 'a'.repeat(32),
          join_date: '2026-05-23T22:00:00Z',
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    renderJoin();
    fillAndSubmit('micah');

    await waitFor(() => {
      expect(screen.getByText(/Welcome, micah\./)).toBeInTheDocument();
    });
    expect(screen.getByText('a'.repeat(32))).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Copy token' })).toBeInTheDocument();
  });

  it('shows an inline error on 409 username_taken', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: 'username_taken', message: 'taken' },
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    renderJoin();
    fillAndSubmit('micah');

    await waitFor(() => {
      expect(
        screen.getByText('That username is already taken.'),
      ).toBeInTheDocument();
    });
    // form is still visible — user can retry
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
  });

  it('shows the API message on 422 invalid_username', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: 'invalid_username',
            message:
              'Username must be 1-30 characters of letters, digits, or underscore.',
          },
        }),
        { status: 422, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    renderJoin();
    fillAndSubmit('bad!');

    await waitFor(() => {
      expect(
        screen.getByText(
          'Username must be 1-30 characters of letters, digits, or underscore.',
        ),
      ).toBeInTheDocument();
    });
  });

  it('disables the submit button while the request is in flight', async () => {
    let resolve: (r: Response) => void = () => {};
    globalThis.fetch = vi.fn().mockReturnValue(
      new Promise<Response>((r) => {
        resolve = r;
      }),
    );

    renderJoin();
    fillAndSubmit('micah');

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Joining…' }),
      ).toBeDisabled();
    });

    resolve(
      new Response(
        JSON.stringify({
          username: 'micah',
          token: 'b'.repeat(32),
          join_date: '2026-05-23T22:00:00Z',
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    await waitFor(() => {
      expect(screen.getByText(/Welcome, micah\./)).toBeInTheDocument();
    });
  });
});
