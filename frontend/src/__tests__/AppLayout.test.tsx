import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import AppLayout from '@/components/layout/AppLayout';
import { supabase } from '@/lib/supabase';

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={['/feed']}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/feed" element={<div>feed body</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

/**
 * Build a Supabase session object shaped enough to satisfy
 * useAuthSession's readUsername path. The hook reads
 * `user.user_metadata.username`; everything else on the session is
 * irrelevant for this layout test, so it's typed as `any` rather
 * than dragging in the full Supabase types.
 */
function fakeSession(username: string) {
  return {
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
  } as unknown as Awaited<
    ReturnType<typeof supabase.auth.getSession>
  >['data']['session'];
}

beforeEach(() => {
  // Default to signed-out. Individual tests override via the mock.
  vi.mocked(supabase.auth.getSession).mockResolvedValue({
    data: { session: null },
  } as Awaited<ReturnType<typeof supabase.auth.getSession>>);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('AppLayout profile icon', () => {
  it('links to /users when no current user is set', async () => {
    renderLayout();
    // useAuthSession runs getSession() in a useEffect; wait for the
    // initial null-session resolution before asserting the link.
    await waitFor(() => {
      const links = screen.getAllByRole('link', { name: /your profile/i });
      expect(links.length).toBeGreaterThanOrEqual(1);
    });
    const links = screen.getAllByRole('link', { name: /your profile/i });
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/users');
    }
  });

  it('links to /u/<name> when the signed-in user has a username', async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: fakeSession('alice') },
    } as Awaited<ReturnType<typeof supabase.auth.getSession>>);

    renderLayout();

    await waitFor(() => {
      const links = screen.getAllByRole('link', { name: /your profile/i });
      // The fakeSession resolves asynchronously, so wait until at
      // least one link has flipped to /u/alice.
      const targets = links.map((l) => l.getAttribute('href'));
      expect(targets).toContain('/u/alice');
    });

    const links = screen.getAllByRole('link', { name: /your profile/i });
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/u/alice');
    }
  });
});

describe('AppLayout Join entry', () => {
  it('shows Join link(s) pointing at /join', () => {
    renderLayout();
    const links = screen.getAllByRole('link', { name: /join/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    for (const link of links) {
      expect(link).toHaveAttribute('href', '/join');
    }
  });
});
