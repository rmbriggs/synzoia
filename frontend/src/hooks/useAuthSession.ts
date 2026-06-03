import { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';

import { supabase } from '@/lib/supabase';

/**
 * Subscribes to the Supabase Auth session for the lifetime of the
 * component that mounts this hook. Replaces the pre-C2
 * `useCurrentUser` hook, which was a localStorage-only "remember
 * this string" pattern with no real verification — the project spec
 * (bronze invariant #5) calls that out as not-enough.
 *
 * What this returns:
 *   - `session`: the Supabase session object, or null if signed out.
 *     Has `.access_token` (the JWT we send to /api/*), `.user.id`
 *     (the Supabase UUID), `.user.email`, etc.
 *   - `username`: the username we asked for at signup, mirrored
 *     onto `user_metadata.username` so the UI doesn't need a
 *     round-trip to /api/profiles just to show "@max" in the header.
 *   - `signOut`: clears the session client-side AND tells Supabase
 *     to invalidate the refresh token server-side.
 *   - `loading`: true while the very first `getSession()` is in
 *     flight — distinguishes "not signed in" from "we don't know
 *     yet" so the UI can show a loading spinner instead of flashing
 *     the signed-out view.
 *
 * Why we subscribe instead of polling: `onAuthStateChange` fires
 * synchronously on signIn/signOut and on token-refresh events (the
 * supabase-js client refreshes JWTs ~5 min before expiry). That
 * keeps the React tree in sync without any timers or stale state.
 */
export function useAuthSession() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    // Read whatever session is already stored on the client. This
    // is what makes "signed in across refreshes" work — supabase-js
    // persists the session to localStorage by default, with the
    // refresh token rotating itself transparently.
    supabase.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      setSession(data.session ?? null);
      setLoading(false);
    });

    // Subscribe to every subsequent change — sign-in, sign-out,
    // token refresh. The cleanup removes the subscription on
    // unmount; safe for StrictMode's double-effect because the
    // listener is keyed on the subscription object, not React.
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setLoading(false);
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, []);

  const username = readUsername(session);

  async function signOut(): Promise<void> {
    await supabase.auth.signOut();
    // onAuthStateChange will fire SIGNED_OUT and update state.
  }

  return { session, username, loading, signOut };
}

/**
 * Username lives in two places:
 *
 *   1. Supabase Auth's `user_metadata.username` — set at signup
 *      time via `signUp(email, password, { options: { data: { username } } })`.
 *      The frontend uses this for header chrome.
 *
 *   2. `profiles.username` in our own DB — the source of truth for
 *      every server-side query that joins on user identity. Set in
 *      the same /api/profiles POST that creates the linked row.
 *
 * `user_metadata` is the cheap path for "what should the header
 * say" because it's already in the session, no extra API call.
 * Server queries always read from `profiles` so a manual rename via
 * SQL is visible immediately even before the next signin.
 */
function readUsername(session: Session | null): string | null {
  if (!session) return null;
  const meta = session.user.user_metadata as { username?: unknown };
  if (typeof meta?.username === 'string' && meta.username.length > 0) {
    return meta.username;
  }
  return null;
}

export default useAuthSession;
