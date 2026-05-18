import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch } from '@/api/client';

const mockSession = vi.fn();

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: () => mockSession(),
    },
  },
}));

describe('apiFetch', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    mockSession.mockResolvedValue({ data: { session: null }, error: null });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.clearAllMocks();
  });

  it('returns parsed JSON on 2xx', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const result = await apiFetch<{ ok: boolean }>('/me');
    expect(result).toEqual({ ok: true });
  });

  it('attaches Authorization header when session exists', async () => {
    mockSession.mockResolvedValue({
      data: { session: { access_token: 'tok_abc' } },
      error: null,
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
    globalThis.fetch = fetchMock;

    await apiFetch('/me');

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get('Authorization')).toBe('Bearer tok_abc');
  });

  it('throws ApiError with status, code, message on non-2xx', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: 'not_found', message: 'group not found' } }),
        { status: 404, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    await expect(apiFetch('/groups/xyz')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      code: 'not_found',
      message: 'group not found',
    });
  });

  it('throws ApiError with generic code when body is unparseable', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response('not-json', { status: 500 }),
    );

    const err = await apiFetch('/anything').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(500);
    expect((err as ApiError).code).toBe('unknown');
  });
});
