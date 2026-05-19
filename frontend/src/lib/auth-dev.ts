const KEY = 'synzoia.dev-session';
const CHANGE_EVENT = 'synzoia:dev-auth-change';

export interface DevSession {
  userId: string;
  displayName: string;
  email: string;
  signedInAt: number;
}

function isEnabled(): boolean {
  return import.meta.env.VITE_DEV_FAKE_AUTH === 'true';
}

function read(): DevSession | null {
  if (!isEnabled()) return null;
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as DevSession) : null;
  } catch {
    return null;
  }
}

function emit() {
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

function signIn(displayName: string, email: string): DevSession {
  const session: DevSession = {
    userId: crypto.randomUUID(),
    displayName,
    email,
    signedInAt: Date.now(),
  };
  localStorage.setItem(KEY, JSON.stringify(session));
  emit();
  return session;
}

function signOut(): void {
  localStorage.removeItem(KEY);
  emit();
}

function subscribe(callback: (s: DevSession | null) => void): () => void {
  const handler = () => callback(read());
  // Same-tab notifications come from our custom event (localStorage
  // doesn't fire 'storage' on the tab that wrote it).
  window.addEventListener(CHANGE_EVENT, handler);
  // Cross-tab notifications come from the native storage event.
  const storageHandler = (e: StorageEvent) => {
    if (e.key === KEY || e.key === null) handler();
  };
  window.addEventListener('storage', storageHandler);
  return () => {
    window.removeEventListener(CHANGE_EVENT, handler);
    window.removeEventListener('storage', storageHandler);
  };
}

export const devAuth = { isEnabled, read, signIn, signOut, subscribe };
