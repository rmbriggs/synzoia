import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import ErrorCard from '@/components/ui/ErrorCard';
import PageHeader from '@/components/ui/PageHeader';
import RowListSkeleton from '@/components/ui/RowListSkeleton';
import { getProfiles, type ProfileListEntry } from '@/api/profiles';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function UserRow({ profile }: { profile: ProfileListEntry }) {
  return (
    <li className="border-b border-border/60 last:border-b-0">
      <Link
        to={`/u/${encodeURIComponent(profile.username)}`}
        className="flex items-center gap-4 py-3 hover:text-primary transition-colors"
      >
        <span className="font-medium flex-1 min-w-0 truncate">
          {profile.username}
        </span>
        <span className="font-mono tabular-nums">
          {formatNumber(profile.total_steps_all_time)}
        </span>
      </Link>
    </li>
  );
}

export default function Users() {
  const query = useQuery({
    queryKey: ['profiles', 'list'],
    queryFn: getProfiles,
    staleTime: 60_000,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Users" description="Everyone walking." />

      {query.isPending ? (
        <RowListSkeleton />
      ) : query.isError ? (
        <ErrorCard
          error={query.error}
          onRetry={() => query.refetch()}
          fallbackMessage="Could not load the users list."
        />
      ) : query.data.profiles.length === 0 ? (
        <Card>
          <EmptyState message="No users yet." />
        </Card>
      ) : (
        <Card>
          <ul>
            {query.data.profiles.map((p) => (
              <UserRow key={p.username} profile={p} />
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
