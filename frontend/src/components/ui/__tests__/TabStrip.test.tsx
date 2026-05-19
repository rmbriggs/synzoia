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
  it('highlights the tab matching ?tab= in the URL', () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={['/crews/abc?tab=leaderboard']}>
        <TabStrip tabs={TABS} defaultKey="feed" />
      </MemoryRouter>,
    );
    expect(getByText('Leaderboard').className).toContain('border-indigo-600');
    expect(getByText('Feed').className).toContain('text-slate-500');
  });

  it('falls back to defaultKey when ?tab= is absent', () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={['/crews/abc']}>
        <TabStrip tabs={TABS} defaultKey="feed" />
      </MemoryRouter>,
    );
    expect(getByText('Feed').className).toContain('border-indigo-600');
  });

  it('writes ?tab= when a tab is clicked', () => {
    const captured: { current: URLSearchParams | null } = { current: null };
    const { getByText } = render(
      <MemoryRouter initialEntries={['/crews/abc']}>
        <TabStrip tabs={TABS} defaultKey="feed" />
        <ParamSpy onParams={(p) => { captured.current = p; }} />
      </MemoryRouter>,
    );
    fireEvent.click(getByText('Chat'));
    expect(captured.current?.get('tab')).toBe('chat');
  });
});
