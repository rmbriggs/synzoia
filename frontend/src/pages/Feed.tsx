import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import { ApiError } from '@/api/client';
import {
  getGlobalDaily,
  type GlobalDailyResponse,
  type LeaderboardEntry,
} from '@/api/steps';
import { currentDate, formatDateLong } from '@/lib/dates';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

const formatHeadingDate = formatDateLong;

function StatStrip({ data }: { data: GlobalDailyResponse }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <Card>
        <div className="label-mono text-muted-foreground">Steps today</div>
        <div className="font-display text-3xl mt-1">
          {formatNumber(data.total_steps)}
        </div>
      </Card>
      <Card>
        <div className="label-mono text-muted-foreground">Posting today</div>
        <div className="font-display text-3xl mt-1">
          {formatNumber(data.participating_users)}
        </div>
      </Card>
    </div>
  );
}

function LeaderboardRow({ entry }: { entry: LeaderboardEntry }) {
  return (
    <li className="flex items-center gap-4 py-3 border-b border-border/60 last:border-b-0">
      <span
        className="label-mono w-10 shrink-0 text-muted-foreground"
        aria-label={`Rank ${entry.rank}`}
      >
        #{entry.rank}
      </span>
      <Link
        to={`/u/${encodeURIComponent(entry.username)}`}
        className="font-medium hover:text-primary transition-colors flex-1 min-w-0 truncate"
      >
        {entry.username}
      </Link>
      <span className="font-mono tabular-nums">
        {formatNumber(entry.total)}
      </span>
    </li>
  );
}

function LeaderboardSkeleton() {
  return (
    <Card className="mt-4">
      <ul>
        {Array.from({ length: 5 }).map((_, i) => (
          <li
            key={i}
            className="flex items-center gap-4 py-3 border-b border-border/60 last:border-b-0"
          >
            <span className="h-3 w-8 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 flex-1 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 w-16 bg-muted/60 rounded animate-pulse" />
          </li>
        ))}
      </ul>
    </Card>
  );
}

function ErrorCard({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : 'Could not load the feed.';
  return (
    <Card className="mt-4 border-destructive/40 bg-destructive/5">
      <p className="text-destructive text-sm">{message}</p>
      <Button variant="secondary" className="mt-3" onClick={onRetry}>
        Try again
      </Button>
    </Card>
  );
}

export default function Feed() {
  const today = currentDate();
  const query = useQuery({
    queryKey: ['steps', 'daily', today],
    queryFn: () => getGlobalDaily(today),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Today"
        description={
          query.data ? formatHeadingDate(query.data.date) : 'Public step feed.'
        }
      />

      {query.isPending ? (
        <>
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <div className="h-3 w-20 bg-muted/60 rounded animate-pulse" />
              <div className="h-8 w-24 bg-muted/60 rounded mt-2 animate-pulse" />
            </Card>
            <Card>
              <div className="h-3 w-20 bg-muted/60 rounded animate-pulse" />
              <div className="h-8 w-24 bg-muted/60 rounded mt-2 animate-pulse" />
            </Card>
          </div>
          <LeaderboardSkeleton />
        </>
      ) : query.isError ? (
        <ErrorCard error={query.error} onRetry={() => query.refetch()} />
      ) : (
        <>
          <StatStrip data={query.data} />
          <Card>
            <h2 className="font-display text-2xl tracking-tight mb-2">
              Leaderboard
            </h2>
            {query.data.leaderboard.length === 0 ? (
              <EmptyState message="No one has posted yet today." />
            ) : (
              <ul>
                {query.data.leaderboard.map((entry) => (
                  <LeaderboardRow key={entry.username} entry={entry} />
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
