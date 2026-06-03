import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';

// Globally stub the Supabase client. The real client throws at import
// time if env vars are missing, would try to open a WebSocket for any
// .channel().subscribe() call in jsdom, and would try to hit the
// Supabase REST API for any .auth.* call. The stub satisfies every
// surface our code touches:
//
//   - `channel` / `removeChannel`: realtime (Feed subscription)
//   - `auth.getSession`: read by apiFetch and useAuthSession on mount
//   - `auth.onAuthStateChange`: subscribed by useAuthSession;
//     the returned subscription has `unsubscribe()` for cleanup
//   - `auth.signInWithPassword` / `signUp` / `signOut`: the auth
//     mutation paths in /login and /join
//
// Tests that need to assert auth-state-driven behavior can override
// this with `vi.mock('@/lib/supabase', ...)` inside the test file.
vi.mock('@/lib/supabase', () => {
  const subscribe = vi.fn(() => ({ unsubscribe: vi.fn() }));
  const on = vi.fn(() => ({ subscribe }));
  const channel = vi.fn(() => ({ on, subscribe }));

  const authSubscription = { subscription: { unsubscribe: vi.fn() } };
  const auth = {
    getSession: vi.fn(() => Promise.resolve({ data: { session: null } })),
    onAuthStateChange: vi.fn(() => ({ data: authSubscription })),
    signInWithPassword: vi.fn(() =>
      Promise.resolve({ data: { session: null, user: null }, error: null }),
    ),
    signUp: vi.fn(() =>
      Promise.resolve({ data: { session: null, user: null }, error: null }),
    ),
    signOut: vi.fn(() => Promise.resolve({ error: null })),
  };

  return {
    supabase: {
      channel,
      removeChannel: vi.fn(),
      auth,
    },
  };
});

// jsdom 29 (the version pinned here) does not expose window.localStorage.
// useTheme persists to it, so provide a minimal in-memory Storage
// polyfill for the test environment only. (Auth state used to live
// here pre-C2; now it lives in Supabase's own client, which is
// mocked above.)
if (typeof window !== 'undefined' && !window.localStorage) {
  class MemoryStorage implements Storage {
    private store = new Map<string, string>();
    get length() {
      return this.store.size;
    }
    clear() {
      this.store.clear();
    }
    getItem(key: string) {
      return this.store.has(key) ? this.store.get(key)! : null;
    }
    key(index: number) {
      return Array.from(this.store.keys())[index] ?? null;
    }
    removeItem(key: string) {
      this.store.delete(key);
    }
    setItem(key: string, value: string) {
      this.store.set(key, String(value));
    }
  }
  const mem = new MemoryStorage();
  Object.defineProperty(window, 'localStorage', {
    value: mem,
    configurable: true,
  });
}

// Keep persisted state from leaking between tests.
afterEach(() => {
  try {
    window.localStorage?.clear?.();
  } catch {
    /* ignore */
  }
});
