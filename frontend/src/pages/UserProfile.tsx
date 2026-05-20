import { useParams } from 'react-router-dom';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';

export default function UserProfile() {
  const { id } = useParams<{ id: string }>();
  return (
    <>
      <PageHeader
        title={`User ${id}`}
        description="Real display name lands when backend's ready."
      />
      <Card className="mt-6">
        <h2 className="text-lg font-semibold">Streaks</h2>
        <EmptyState message="Current and longest streak appear here." />
      </Card>
      <Card className="mt-4">
        <h2 className="text-lg font-semibold">Recent posts</h2>
        <EmptyState message="Recent posts from crews you share will appear here." />
      </Card>
    </>
  );
}
