import { describe, expect, it } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { MemoryRouter, useSearchParams } from 'react-router-dom';
import TabStrip from '@/components/ui/TabStrip';

const TABS = [
  { key: 'feed', label: 'Feed' },
  { key: 'leaderboard', label: 'Leaderboard' },
  { key: 'chat', label: 'Chat' },
];

// Probe component to inspect search params from inside the router.
function ParamSpy({ onParams }: { onParams: (s: URLSearchParams) => void }) {
  const [params] = useSearchParams();
  onParams(params);
  return null;
}

describe('TabStrip', () => {
  it('marks the tab matching ?tab= as active', () => {
    const { getByRole } = render(
      <MemoryRouter initialEntries={['/crews/abc?tab=leaderboard']}>
        <TabStrip tabs={TABS} defaultKey="feed" />
      </MemoryRouter>,
    );
    expect(getByRole('tab', { name: 'Leaderboard' })).toHaveAttribute('data-state', 'active');
    expect(getByRole('tab', { name: 'Feed' })).toHaveAttribute('data-state', 'inactive');
  });

  it('falls back to defaultKey when ?tab= is absent', () => {
    const { getByRole } = render(
      <MemoryRouter initialEntries={['/crews/abc']}>
        <TabStrip tabs={TABS} defaultKey="feed" />
      </MemoryRouter>,
    );
    expect(getByRole('tab', { name: 'Feed' })).toHaveAttribute('data-state', 'active');
  });

  it('writes ?tab= when a tab is clicked', () => {
    const captured: { current: URLSearchParams | null } = { current: null };
    const { getByRole } = render(
      <MemoryRouter initialEntries={['/crews/abc']}>
        <TabStrip tabs={TABS} defaultKey="feed" />
        <ParamSpy onParams={(p) => { captured.current = p; }} />
      </MemoryRouter>,
    );
    const chatTab = getByRole('tab', { name: 'Chat' });
    fireEvent.mouseDown(chatTab, { button: 0, ctrlKey: false });
    expect(captured.current?.get('tab')).toBe('chat');
  });
});
