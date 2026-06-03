import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import Join from '@/pages/Join';
import { supabase } from '@/lib/supabase';

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

/**
 * Signup is a two-call sequence post-C2:
 *   1. supabase.auth.signUp(email, password, { data: { username } })
 *   2. POST /api/profiles { username } with the just-installed JWT
 *
 * Helpers below stub each side independently so tests can mix-and-
 * match (success/fail at either layer).
 */

function mockSupabaseSignUpOk() {
  vi.mocked(supabase.auth.signUp).mockResolvedValue({
    data: {
      session: {
        access_token: 'fake-jwt',
        refresh_token: 'fake-refresh',
        expires_at: 9_999_999_999,
        expires_in: 3600,
        token_type: 'bearer',
        user: {
          id: 'fake-uuid',
          email: 'micah@example.com',
          user_metadata: { username: 'micah' },
          app_metadata: {},
          aud: 'authenticated',
          created_at: '2026-05-01T00:00:00Z',
        },
      } as Parameters<typeof vi.mocked>[0],
      user: null,
    },
    error: null,
  } as Awaited<ReturnType<typeof supabase.auth.signUp>>);
}

function mockSupabaseSignUpFail(message: string) {
  vi.mocked(supabase.auth.signUp).mockResolvedValue({
    data: { session: null, user: null },
    error: { message, name: 'AuthError', status: 400 },
  } as Awaited<ReturnType<typeof supabase.auth.signUp>>);
}

function fillAndSubmit({
  username = 'micah',
  email = 'micah@example.com',
  password = 'hunter2hunter2',
}: {
  username?: string;
  email?: string;
  password?: string;
} = {}) {
  fireEvent.change(screen.getByLabelText('Email'), {
    target: { value: email },
  });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: password },
  });
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
    mockSupabaseSignUpOk();
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
    fillAndSubmit();

    await waitFor(() => {
      // Eventually shows the real token (not just the optimistic
      // placeholder), which is the signal that BOTH Supabase signup
      // AND the /api/profiles call completed.
      expect(screen.getByText('a'.repeat(32))).toBeInTheDocument();
    });
    expect(screen.getByText(/Welcome, micah\./)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Copy token' }),
    ).toBeInTheDocument();
  });

  it('optimistically shows the welcome screen before the server confirms', async () => {
    // Block the /api/profiles call indefinitely so we can observe
    // the optimistic state — silver invariant "optimistic updates
    // on at least one action."
    let resolveProfile: (r: Response) => void = () => {};
    mockSupabaseSignUpOk();
    globalThis.fetch = vi.fn().mockReturnValue(
      new Promise<Response>((r) => {
        resolveProfile = r;
      }),
    );

    renderJoin();
    fillAndSubmit();

    // While the network is in flight, the welcome screen should
    // already be visible (optimistic).
    await waitFor(() => {
      expect(screen.getByText(/Welcome, micah\./)).toBeInTheDocument();
    });
    // The Copy button is rendered but disabled because the real
    // token hasn't arrived yet.
    expect(
      screen.getByRole('button', { name: /Almost there/ }),
    ).toBeDisabled();

    // Resolve the network → token block fills in, button enables.
    resolveProfile(
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
      expect(screen.getByText('b'.repeat(32))).toBeInTheDocument();
    });
  });

  it('rolls back to the form when Supabase signup fails', async () => {
    mockSupabaseSignUpFail('User already registered');

    renderJoin();
    fillAndSubmit();

    // The optimistic welcome briefly flips on then rolls back to
    // the form when onError fires. By the time the assertion runs,
    // the form is visible again.
    await waitFor(() => {
      expect(screen.getByLabelText('Username')).toBeInTheDocument();
    });
    expect(
      screen.getByText('That email already has an account. Try signing in instead.'),
    ).toBeInTheDocument();
  });

  it('shows an inline error on 409 username_taken', async () => {
    mockSupabaseSignUpOk();
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: 'username_taken', message: 'taken' },
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    renderJoin();
    fillAndSubmit();

    await waitFor(() => {
      expect(
        screen.getByText('That username is already taken.'),
      ).toBeInTheDocument();
    });
    // form is back (rollback) — user can retry with a new username
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
  });

  it('shows the API message on 422 invalid_username', async () => {
    mockSupabaseSignUpOk();
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
    fillAndSubmit({ username: 'bad!' });

    await waitFor(() => {
      expect(
        screen.getByText(
          'Username must be 1-30 characters of letters, digits, or underscore.',
        ),
      ).toBeInTheDocument();
    });
  });
});
