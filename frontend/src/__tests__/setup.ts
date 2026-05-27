import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';

// jsdom 29 (the version pinned here) does not expose window.localStorage.
// Several features (useTheme, useCurrentUser) persist to it, so provide a
// minimal in-memory Storage polyfill for the test environment only.
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
