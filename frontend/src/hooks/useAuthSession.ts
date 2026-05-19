import { useEffect, useState } from 'react';
import { devAuth, type DevSession } from '@/lib/auth-dev';

export interface AuthSessionState {
  session: DevSession | null;
  loading: boolean;
}

export function useAuthSession(): AuthSessionState {
  const [session, setSession] = useState<DevSession | null>(() => devAuth.read());

  useEffect(() => devAuth.subscribe(setSession), []);

  return { session, loading: false };
}
