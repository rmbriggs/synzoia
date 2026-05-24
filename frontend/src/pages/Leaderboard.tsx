import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import TabStrip from '@/components/ui/TabStrip';
import { ApiError } from '@/api/client';
import {
  getGlobalDaily,
  getGlobalWeekly,
  type DailyTotal,
  type LeaderboardEntry,
} from '@/api/steps';
import { localDate } from '@/lib/dates';

const TABS = [
  { key: 'today', label: 'Today' },
  { key: 'week', label: 'This Week' },
];

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function formatHeadingDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
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
    <Card>
      <ul>
        {Array.from({ length: 6 }).map((_, i) => (
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
        : 'Could not load the leaderboard.';
  return (
    <Card className="border-destructive/40 bg-destructive/5">
      <p className="text-destructive text-sm">{message}</p>
      <Button variant="secondary" className="mt-3" onClick={onRetry}>
        Try again
      </Button>
    </Card>
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
  const today = localDate();
  const query = useQuery({
    queryKey: ['steps', 'daily', today],
    queryFn: () => getGlobalDaily(today),
    staleTime: 30_000,
  });

  if (query.isPending) return <LeaderboardSkeleton />;
  if (query.isError) {
    return <ErrorCard error={query.error} onRetry={() => query.refetch()} />;
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

function WeeklyBars({ days }: { days: DailyTotal[] }) {
  const max = Math.max(...days.map((d) => d.total), 1);
  return (
    <div className="grid grid-cols-7 gap-2 h-28 items-end">
      {days.map((d) => {
        const heightPct = (d.total / max) * 100;
        return (
          <div
            key={d.date}
            className="flex flex-col items-center gap-1.5 h-full"
            title={`${d.date}: ${formatNumber(d.total)}`}
          >
            <div className="flex-1 w-full flex items-end">
              <div
                className="w-full bg-primary/70 rounded-t"
                style={{ height: `${Math.max(heightPct, 2)}%` }}
                aria-label={`${d.date}: ${formatNumber(d.total)} steps`}
              />
            </div>
            <span className="label-mono text-[10px] text-muted-foreground">
              {d.date.slice(-2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function WeeklyPanel() {
  const query = useQuery({
    queryKey: ['steps', 'weekly'],
    queryFn: () => getGlobalWeekly(),
    staleTime: 30_000,
  });

  if (query.isPending) return <LeaderboardSkeleton />;
  if (query.isError) {
    return <ErrorCard error={query.error} onRetry={() => query.refetch()} />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h2 className="font-display text-2xl tracking-tight">
            {formatHeadingDate(query.data.week_start)} –{' '}
            {formatHeadingDate(query.data.week_end)}
          </h2>
          <span className="label-mono text-muted-foreground">
            {formatNumber(query.data.total_steps)} total steps
          </span>
        </div>
        <WeeklyBars days={query.data.daily_breakdown} />
      </Card>
      <Card>
        <h3 className="font-display text-xl tracking-tight mb-1">
          Standings
        </h3>
        <LeaderboardList
          leaderboard={query.data.leaderboard}
          emptyMessage="No one has posted yet this week."
        />
      </Card>
    </div>
  );
}

export default function Leaderboard() {
  const [params] = useSearchParams();
  const active = params.get('tab') ?? 'week';

  return (
    <div className="space-y-6">
      <PageHeader
        title="Leaderboard"
        description="Step rankings across all members."
      />
      <TabStrip tabs={TABS} defaultKey="week" />
      {active === 'today' ? <TodayPanel /> : <WeeklyPanel />}
    </div>
  );
}
