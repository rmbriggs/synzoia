import type { Session } from '@supabase/supabase-js';

export interface AuthSessionState {
  session: Session | null;
  loading: boolean;
}

/**
 * Stub. Real implementation (subscribes to supabase.auth.onAuthStateChange)
 * lands when the /auth page does. Returns logged-out + not-loading so
 * pages can render without errors during scaffolding.
 */
export function useAuthSession(): AuthSessionState {
  return { session: null, loading: false };
}
