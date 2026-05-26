import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Users from '@/pages/Users';
import * as profilesApi from '@/api/profiles';

function renderUsers() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/users']}>
        <Users />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Users page', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders profiles alphabetically', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      profiles: [
        { username: 'alice', join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 9000 },
        { username: 'bob',   join_date: '2026-05-20T00:00:00Z', total_steps_all_time: 4000 },
      ],
    });

    renderUsers();
    await waitFor(() => expect(screen.getByText('alice')).toBeInTheDocument());
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.getByText('9,000')).toBeInTheDocument();
  });

  it('each row links to /u/<username>', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      profiles: [
        { username: 'alice', join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 0 },
      ],
    });

    renderUsers();
    const link = await screen.findByRole('link', { name: /alice/ });
    expect(link).toHaveAttribute('href', '/u/alice');
  });

  it('shows empty state when there are no users', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({ profiles: [] });

    renderUsers();
    await waitFor(() => expect(screen.getByText(/no users yet/i)).toBeInTheDocument());
  });
});
