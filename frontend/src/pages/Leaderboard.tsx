import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import ErrorCard from '@/components/ui/ErrorCard';
import PageHeader from '@/components/ui/PageHeader';
import RowListSkeleton from '@/components/ui/RowListSkeleton';
import TabStrip from '@/components/ui/TabStrip';
import {
  getGlobalDaily,
  getGlobalRanking,
  type LeaderboardEntry,
} from '@/api/steps';
import { currentDate } from '@/lib/dates';

const TABS = [
  { key: 'today', label: 'Today' },
  { key: 'ranking', label: 'Last 30 days' },
];

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function formatHeadingDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
  });
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
        @{entry.username}
      </Link>
      <span className="font-mono tabular-nums">
        {formatNumber(entry.total)}
      </span>
    </li>
  );
}

function LeaderboardList({
  leaderboard,
  emptyMessage,
}: {
  leaderboard: LeaderboardEntry[];
  emptyMessage: string;
}) {
  if (leaderboard.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }
  return (
    <ul>
      {leaderboard.map((entry) => (
        <LeaderboardRow key={entry.username} entry={entry} />
      ))}
    </ul>
  );
}

function TodayPanel() {
  const today = currentDate();
  const query = useQuery({
    queryKey: ['steps', 'daily', today],
    queryFn: () => getGlobalDaily(today),
    staleTime: 30_000,
  });

  if (query.isPending) return <RowListSkeleton />;
  if (query.isError) {
    return (
      <ErrorCard
        error={query.error}
        onRetry={() => query.refetch()}
        fallbackMessage="Could not load the leaderboard."
      />
    );
  }

  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <h2 className="font-display text-2xl tracking-tight">
          {formatHeadingDate(query.data.date)}
        </h2>
        <span className="label-mono text-muted-foreground">
          {formatNumber(query.data.total_steps)} total steps
        </span>
      </div>
      <LeaderboardList
        leaderboard={query.data.leaderboard}
        emptyMessage="No one has posted yet today."
      />
    </Card>
  );
}

function RankingPanel() {
  const today = currentDate();
  const query = useQuery({
    queryKey: ['steps', 'ranking', today],
    queryFn: () => getGlobalRanking(today),
    staleTime: 30_000,
  });

  if (query.isPending) return <RowListSkeleton />;
  if (query.isError) {
    return (
      <ErrorCard
        error={query.error}
        onRetry={() => query.refetch()}
        fallbackMessage="Could not load the leaderboard."
      />
    );
  }

  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <h2 className="font-display text-2xl tracking-tight">Last 30 days</h2>
        <span className="label-mono text-muted-foreground">
          {formatNumber(query.data.total_steps)} total steps
        </span>
      </div>
      <LeaderboardList
        leaderboard={query.data.leaderboard}
        emptyMessage="No one has posted in the last 30 days."
      />
    </Card>
  );
}

export default function Leaderboard() {
  const [params] = useSearchParams();
  const active = params.get('tab') ?? 'today';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Leaderboard"
        description="Step rankings across all members."
      />
      <TabStrip tabs={TABS} defaultKey="today" />
      {active === 'today' ? <TodayPanel /> : <RankingPanel />}
    </div>
  );
}
