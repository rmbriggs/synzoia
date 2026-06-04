import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Users from '@/pages/Users';
import * as profilesApi from '@/api/profiles';
import * as stepsApi from '@/api/steps';
import * as sleepApi from '@/api/sleep';

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
    vi.useRealTimers();
  });

  it('lists profiles oldest-joined first, with an @ prefix', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      // Returned newest-first on purpose; the page re-sorts by join date.
      profiles: [
        { username: 'alice', join_date: '2026-05-20T00:00:00Z', total_steps_all_time: 9000 },
        { username: 'zoe',   join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 4000 },
      ],
    });

    renderUsers();
    await waitFor(() => expect(screen.getByText('@zoe')).toBeInTheDocument());
    expect(screen.getByText('@alice')).toBeInTheDocument();
    // Total-steps count was removed from this page — it shouldn't render.
    expect(screen.queryByText('9,000')).not.toBeInTheDocument();

    // Oldest join_date (zoe, 05-19) renders above the newer one (alice, 05-20).
    const names = screen.getAllByRole('link').map((l) => l.textContent);
    expect(names[0]).toContain('@zoe');
    expect(names[1]).toContain('@alice');
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

  it('prefetches a user\'s summary data on hover', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      profiles: [
        { username: 'alice', join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 9000 },
      ],
    });
    const stepsSummary = vi
      .spyOn(stepsApi, 'getUserSummary')
      .mockResolvedValue({} as never);
    const sleepSummary = vi
      .spyOn(sleepApi, 'getUserSummary')
      .mockResolvedValue({} as never);
    // Silence the rest of the prefetch fan-out.
    vi.spyOn(stepsApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserMonthly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserMonthly').mockResolvedValue({} as never);

    renderUsers();
    const link = await screen.findByRole('link', { name: /alice/ });

    // Nothing prefetched until the row is hovered.
    expect(stepsSummary).not.toHaveBeenCalled();

    fireEvent.mouseEnter(link);

    await waitFor(() => expect(stepsSummary).toHaveBeenCalledWith('alice'));
    expect(sleepSummary).toHaveBeenCalledWith('alice');
  });

  it('prefetches on keyboard focus (touch/keyboard users have no hover)', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      profiles: [
        { username: 'alice', join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 9000 },
      ],
    });
    const stepsSummary = vi
      .spyOn(stepsApi, 'getUserSummary')
      .mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserSummary').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserMonthly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserMonthly').mockResolvedValue({} as never);

    renderUsers();
    const link = await screen.findByRole('link', { name: /alice/ });
    expect(stepsSummary).not.toHaveBeenCalled();

    fireEvent.focus(link);

    await waitFor(() => expect(stepsSummary).toHaveBeenCalledWith('alice'));
  });

  it('waits for the hover-intent delay before prefetching (a quick pass-over fires nothing)', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      profiles: [
        { username: 'alice', join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 9000 },
      ],
    });
    const stepsSummary = vi
      .spyOn(stepsApi, 'getUserSummary')
      .mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserSummary').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserMonthly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserMonthly').mockResolvedValue({} as never);

    renderUsers();
    const link = await screen.findByRole('link', { name: /alice/ });

    vi.useFakeTimers();
    try {
      fireEvent.mouseEnter(link);
      // Still inside the intent window — a cursor merely passing over the
      // row should not have triggered the 8-request fan-out yet.
      vi.advanceTimersByTime(50);
      expect(stepsSummary).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });

  it('cancels the prefetch if the cursor leaves before the delay elapses', async () => {
    vi.spyOn(profilesApi, 'getProfiles').mockResolvedValue({
      profiles: [
        { username: 'alice', join_date: '2026-05-19T00:00:00Z', total_steps_all_time: 9000 },
      ],
    });
    const stepsSummary = vi
      .spyOn(stepsApi, 'getUserSummary')
      .mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserSummary').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(stepsApi, 'getUserMonthly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserDaily').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserWeekly').mockResolvedValue({} as never);
    vi.spyOn(sleepApi, 'getUserMonthly').mockResolvedValue({} as never);

    renderUsers();
    const link = await screen.findByRole('link', { name: /alice/ });

    vi.useFakeTimers();
    try {
      fireEvent.mouseEnter(link);
      fireEvent.mouseLeave(link);
      // Even well past the delay, the cancelled prefetch never runs.
      vi.advanceTimersByTime(500);
      expect(stepsSummary).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });
});
