import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '@/App';

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
    },
  },
}));

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
    '/auth',
    '/crews',
    '/crews/abc',
    '/crews/abc/post',
    '/users/xyz',
    '/settings',
  ];

  for (const route of routes) {
    it(`renders an <h1> at ${route}`, () => {
      const { container } = renderAt(route);
      const headings = container.querySelectorAll('h1');
      expect(headings.length).toBeGreaterThanOrEqual(1);
    });
  }

  it('redirects "/" to /auth when logged out', () => {
    const { container } = renderAt('/');
    // The "Sleep with friends." tagline only exists on /auth, so seeing it
    // here proves we actually redirected (vs. rendering Home directly).
    expect(container.textContent).toContain('Sleep with friends.');
  });
});
