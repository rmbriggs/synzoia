import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch } from '@/api/client';

describe('apiFetch', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
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

  it('sets Content-Type: application/json when a body is provided', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('{}', {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    globalThis.fetch = fetchMock;

    await apiFetch('/profiles', {
      method: 'POST',
      body: JSON.stringify({ username: 'micah' }),
    });

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get('Content-Type')).toBe('application/json');
  });

  it('throws ApiError with status, code, message on non-2xx', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: 'username_taken', message: 'taken' },
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    await expect(apiFetch('/profiles')).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      code: 'username_taken',
      message: 'taken',
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
