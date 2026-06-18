import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '@/App';

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('App smoke', () => {
  const routes = [
    '/',
    '/join',
    '/style-guide',
    '/db',
    '/feed',
    '/users',
    '/leaderboard',
    '/u/someuser',
  ];

  for (const route of routes) {
    it(`renders an <h1> at ${route}`, () => {
      const { container } = renderAt(route);
      const headings = container.querySelectorAll('h1');
      expect(headings.length).toBeGreaterThanOrEqual(1);
    });
  }

  it('renders the Landing marketing page at "/"', () => {
    const { container } = renderAt('/');
    // "/" now renders the Landing page (SP3 redesign). The Feed is at /feed.
    expect(container.textContent).toContain('Wide open.');
    expect(container.textContent).not.toContain('Recent milestones and recaps.');
  });
});
