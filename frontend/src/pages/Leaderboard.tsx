import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import ErrorCard from '@/components/ui/ErrorCard';
import PageHeader from '@/components/ui/PageHeader';
import RowListSkeleton from '@/components/ui/RowListSkeleton';
import TabStrip from '@/components/ui/TabStrip';
import UserAvatar from '@/components/ui/UserAvatar';
import {
  getGlobalDaily,
  getGlobalRanking,
  type LeaderboardEntry,
} from '@/api/steps';
import { getSleepRanking } from '@/api/sleep';
import { currentDate } from '@/lib/dates';

const TABS = [
  { key: 'today', label: 'Today' },
  { key: 'ranking', label: 'Last 30 days' },
  { key: 'sleep', label: 'Sleep' },
];

// Medal accent config for top-3 ranks.
// Gold uses --amber token, bronze uses --bark token, silver uses an inline
// oklch tint (no token maps cleanly to a neutral silver in the coastal palette).
const MEDAL_STYLES: Record<
  number,
  { label: string; badgeCls: string; ringStyle?: React.CSSProperties }
> = {
  1: {
    label: 'Gold',
    badgeCls: 'text-[color:var(--amber)] font-bold',
    ringStyle: { boxShadow: '0 0 0 2px var(--amber)' },
  },
  2: {
    label: 'Silver',
    badgeCls: 'font-bold',
    ringStyle: { boxShadow: '0 0 0 2px oklch(0.72 0.02 240)' },
  },
  3: {
    label: 'Bronze',
    badgeCls: 'text-[color:var(--bark)] font-bold',
    ringStyle: { boxShadow: '0 0 0 2px var(--bark)' },
  },
};

const MEDAL_EMOJI: Record<number, string> = {
  1: '🥇',
  2: '🥈',
  3: '🥉',
};

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

/** Format minutes as "Xh Ym" (e.g. 437 → "7h 17m"). */
function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

type RowProps = {
  entry: LeaderboardEntry;
  formatTotal?: (n: number) => string;
};

function CoastalLeaderboardRow({ entry, formatTotal = formatNumber }: RowProps) {
  const medal = MEDAL_STYLES[entry.rank];
  const rankLabel = medal ? MEDAL_EMOJI[entry.rank] : `#${entry.rank}`;

  return (
    <li className="flex items-center gap-4 py-3 border-b border-border/60 last:border-b-0">
      {/* Rank badge */}
      <span
        className={`label-mono w-8 shrink-0 text-center select-none ${medal ? medal.badgeCls : 'text-muted-foreground'}`}
        aria-label={`Rank ${entry.rank}${medal ? ` – ${medal.label}` : ''}`}
        title={medal ? medal.label : undefined}
      >
        {rankLabel}
      </span>

      {/* Avatar with medal ring for top 3 */}
      <div
        className="shrink-0 rounded-full"
        style={medal?.ringStyle}
      >
        <UserAvatar username={entry.username} size="sm" />
      </div>

      {/* Username link */}
      <Link
        to={`/u/${encodeURIComponent(entry.username)}`}
        className="font-medium hover:text-primary transition-colors flex-1 min-w-0 truncate"
      >
        @{entry.username}
      </Link>

      {/* Total */}
      <span className="font-mono tabular-nums text-sm shrink-0">
        {formatTotal(entry.total)}
      </span>
    </li>
  );
}

function CoastalLeaderboardList({
  leaderboard,
  emptyMessage,
  formatTotal,
}: {
  leaderboard: LeaderboardEntry[];
  emptyMessage: string;
  formatTotal?: (n: number) => string;
}) {
  if (leaderboard.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }
  return (
    <ul>
      {leaderboard.map((entry) => (
        <CoastalLeaderboardRow
          key={entry.username}
          entry={entry}
          formatTotal={formatTotal}
        />
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
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h2 className="font-display text-2xl tracking-tight">
          {formatHeadingDate(query.data.date)}
        </h2>
        <span className="label-mono text-muted-foreground">
          {formatNumber(query.data.total_steps)} total steps
        </span>
      </div>
      <CoastalLeaderboardList
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
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h2 className="font-display text-2xl tracking-tight">Last 30 days</h2>
        <span className="label-mono text-muted-foreground">
          {formatNumber(query.data.total_steps)} total steps
        </span>
      </div>
      <CoastalLeaderboardList
        leaderboard={query.data.leaderboard}
        emptyMessage="No one has posted in the last 30 days."
      />
    </Card>
  );
}

function SleepPanel() {
  const query = useQuery({
    queryKey: ['sleep', 'ranking'],
    queryFn: getSleepRanking,
    staleTime: 60_000,
  });

  if (query.isPending) return <RowListSkeleton />;
  if (query.isError) {
    return (
      <ErrorCard
        error={query.error}
        onRetry={() => query.refetch()}
        fallbackMessage="Could not load the sleep leaderboard."
      />
    );
  }

  const { week_start, week_end, leaderboard } = query.data;
  const weekLabel = `${formatHeadingDate(week_start)} – ${formatHeadingDate(week_end)}`;

  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <h2 className="font-display text-2xl tracking-tight">Sleep</h2>
        <span className="label-mono text-muted-foreground">{weekLabel}</span>
      </div>
      <CoastalLeaderboardList
        leaderboard={leaderboard}
        emptyMessage="No sleep data logged this week."
        formatTotal={formatMinutes}
      />
    </Card>
  );
}

export default function Leaderboard() {
  const [params] = useSearchParams();
  const active = params.get('tab') ?? 'today';

  let panel: React.ReactNode;
  if (active === 'today') panel = <TodayPanel />;
  else if (active === 'ranking') panel = <RankingPanel />;
  else panel = <SleepPanel />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Leaderboard"
        description="Step and sleep rankings across all members."
      />
      <TabStrip tabs={TABS} defaultKey="today" />
      {panel}
    </div>
  );
}
