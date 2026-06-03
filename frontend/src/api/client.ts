/**
 * Cache key convention (used with @tanstack/react-query):
 *   ['profiles', username]
 * Keys are arrays mirroring the URL.
 *
 * Auth (post-C2): every call attaches the current Supabase Auth
 * access token as `Authorization: Bearer <jwt>` if a session exists.
 * Unauthenticated reads still work for endpoints that allow it
 * (global aggregations); endpoints that require a user (e.g.
 * /api/profiles POST, per-user reads) return 401 without a token.
 *
 * The iOS Shortcut sends its own opaque-token header out-of-band —
 * the website never sees it.
 */

import { supabase } from '@/lib/supabase';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export class ApiError extends Error {
  name = 'ApiError';
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/**
 * Read the current Supabase session's access token if there is one.
 * Returns null if the user isn't signed in (which is fine for
 * endpoints that allow anonymous reads). Wrapped in a try/catch
 * because `getSession` returns a Promise but may also throw if the
 * supabase-js client hasn't been initialized in this environment
 * (notably under jsdom in tests, where we stub the module).
 */
async function currentAccessToken(): Promise<string | null> {
  try {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  } catch {
    return null;
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // Attach the Supabase JWT if a session exists and the caller
  // hasn't already set an Authorization header (e.g. a one-off
  // call with a custom credential).
  if (!headers.has('Authorization')) {
    const token = await currentAccessToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let code = 'unknown';
    let message = res.statusText || 'Request failed';
    try {
      const body = (await res.json()) as { error?: { code?: string; message?: string } };
      if (body.error?.code) code = body.error.code;
      if (body.error?.message) message = body.error.message;
    } catch {
      // body wasn't JSON; keep defaults
    }
    throw new ApiError(res.status, code, message);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}
