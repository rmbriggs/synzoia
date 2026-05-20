import { Navigate } from 'react-router-dom';
import { useAuthSession } from '@/hooks/useAuthSession';
import Landing from '@/pages/Landing';

export default function Home() {
  const { session, loading } = useAuthSession();
  if (loading) {
    return <p className="p-6">Loading…</p>;
  }
  if (session) {
    return <Navigate to="/crews" replace />;
  }
  return <Landing />;
}
