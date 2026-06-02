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

  it('renders the Feed at "/" (the default view)', () => {
    const { container } = renderAt('/');
    // "/" now redirects to /feed. The Feed's description is unique to it;
    // the Landing headline must no longer appear at the default route.
    expect(container.textContent).toContain('Recent milestones and recaps.');
    expect(container.textContent).not.toContain('More than a step counter.');
  });
});
