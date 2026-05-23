import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '@/App';

vi.mock('@/hooks/useAuthSession', () => ({
  useAuthSession: () => ({ session: null, loading: false }),
}));

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
    '/dashboard',
    '/crews',
    '/crews/abc',
    '/crews/abc/post',
    '/users/xyz',
    '/settings',
    '/style-guide',
  ];

  for (const route of routes) {
    it(`renders an <h1> at ${route}`, () => {
      const { container } = renderAt(route);
      const headings = container.querySelectorAll('h1');
      expect(headings.length).toBeGreaterThanOrEqual(1);
    });
  }

  it('renders the landing page at "/" when logged out', () => {
    const { container } = renderAt('/');
    // The "More than sleep tracking." headline is unique to the landing page.
    expect(container.textContent).toContain('More than sleep tracking.');
  });
});
