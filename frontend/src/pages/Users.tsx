import { useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import ErrorCard from '@/components/ui/ErrorCard';
import PageHeader from '@/components/ui/PageHeader';
import RowListSkeleton from '@/components/ui/RowListSkeleton';
import UserAvatar from '@/components/ui/UserAvatar';
import { getProfiles, type ProfileListEntry } from '@/api/profiles';
import { userSummaryQueries } from '@/api/userSummaryQueries';
import { currentDate, lastNightDate } from '@/lib/dates';

// How long the cursor must rest on a row before we warm its profile
// queries. Long enough to skip rows the cursor merely sweeps past on the
// way down the list, short enough that a deliberate pause still feels
// instant on click. Keyboard focus bypasses this — see onFocus below.
const HOVER_PREFETCH_DELAY_MS = 100;

function UserRow({ profile }: { profile: ProfileListEntry }) {
  const queryClient = useQueryClient();
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Warm the 8 Summary-tab queries so clicking through renders instantly.
  // prefetchQuery respects staleTime, so repeat hovers within 30s are
  // no-ops, and a failed prefetch is swallowed (Profile just loads
  // normally on click).
  const prefetch = () => {
    const today = currentDate();
    const lastNight = lastNightDate();
    for (const q of userSummaryQueries(profile.username, today, lastNight)) {
      queryClient.prefetchQuery(q);
    }
  };

  // Hover prefetch is gated behind HOVER_PREFETCH_DELAY_MS so a cursor
  // sweeping down the list doesn't fire an 8-request fan-out per row it
  // passes over. Leaving the row before the delay cancels the pending
  // prefetch. Keyboard focus is deliberate (you can't accidentally
  // focus-sweep), so it prefetches immediately for snappier a11y.
  const startHoverPrefetch = () => {
    hoverTimer.current = setTimeout(prefetch, HOVER_PREFETCH_DELAY_MS);
  };
  const cancelHoverPrefetch = () => {
    if (hoverTimer.current) {
      clearTimeout(hoverTimer.current);
      hoverTimer.current = null;
    }
  };

  // Drop a pending timer if the row unmounts (e.g. the user clicks
  // through before the delay elapses) so it can't fire after navigation.
  useEffect(() => {
    return () => {
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
    };
  }, []);

  return (
    <li className="flex items-center gap-4 py-3 border-b border-border/60 last:border-b-0">
      {/* Avatar */}
      <div className="shrink-0">
        <UserAvatar username={profile.username} size="sm" />
      </div>

      {/* Username link */}
      <Link
        to={`/u/${encodeURIComponent(profile.username)}`}
        onMouseEnter={startHoverPrefetch}
        onMouseLeave={cancelHoverPrefetch}
        onFocus={prefetch}
        onBlur={cancelHoverPrefetch}
        className="font-medium hover:text-primary transition-colors flex-1 min-w-0 truncate"
      >
        @{profile.username}
      </Link>

      {/* All-time steps */}
      <span className="font-mono tabular-nums text-sm text-muted-foreground shrink-0">
        {profile.total_steps_all_time.toLocaleString()} steps
      </span>
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
            {[...query.data.profiles]
              // Oldest member first. join_date is an ISO timestamp, so a
              // plain string compare sorts chronologically.
              .sort((a, b) => a.join_date.localeCompare(b.join_date))
              .map((p) => (
                <UserRow key={p.username} profile={p} />
              ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
