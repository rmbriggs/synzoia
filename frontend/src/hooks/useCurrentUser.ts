import { useEffect, useState } from 'react';

const STORAGE_KEY = 'synzoia.currentUser';
const SYNC_EVENT = 'synzoia:currentuser';

function readStored(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const v = window.localStorage?.getItem?.(STORAGE_KEY);
    return v && v.length > 0 ? v : null;
  } catch {
    return null;
  }
}

function writeStored(username: string) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage?.setItem?.(STORAGE_KEY, username);
  } catch {
    /* swallow — feature-detect, don't throw */
  }
}

function clearStored() {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage?.removeItem?.(STORAGE_KEY);
  } catch {
    /* swallow */
  }
}

/**
 * Client-side "current user" pointer, persisted to localStorage.
 *
 * Purely a browser convenience — there's no auth. Multiple hook
 * instances stay in sync within a tab via a custom window event
 * (dispatched on every write) and across tabs via the native
 * `storage` event. Mirrors the localStorage discipline in useTheme.
 */
export function useCurrentUser() {
  const [currentUser, setState] = useState<string | null>(() => readStored());

  useEffect(() => {
    function resync() {
      setState(readStored());
    }
    window.addEventListener(SYNC_EVENT, resync);
    window.addEventListener('storage', resync);
    return () => {
      window.removeEventListener(SYNC_EVENT, resync);
      window.removeEventListener('storage', resync);
    };
  }, []);

  function setCurrentUser(username: string) {
    writeStored(username);
    setState(username);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(SYNC_EVENT));
    }
  }

  function clearCurrentUser() {
    clearStored();
    setState(null);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(SYNC_EVENT));
    }
  }

  return { currentUser, setCurrentUser, clearCurrentUser };
}

export default useCurrentUser;
