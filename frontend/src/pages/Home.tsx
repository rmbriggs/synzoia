import { Navigate } from 'react-router-dom';
import { useAuthSession } from '@/hooks/useAuthSession';

export default function Home() {
  const { session, loading } = useAuthSession();
  if (loading) {
    return <p className="p-6">Loading…</p>;
  }
  return <Navigate to={session ? '/crews' : '/auth'} replace />;
}
