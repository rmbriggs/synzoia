import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import { ApiError } from '@/api/client';
import {
  getUserDaily,
  getUserSummary,
  getUserWeekly,
  type DailyTotal,
  type UserSummaryResponse,
  type UserWeeklyResponse,
  type UserDailyResponse,
} from '@/api/steps';
import {
  currentDate,
  formatDateMedium,
  formatTimestampDate,
} from '@/lib/dates';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

const formatHeadingDate = formatDateMedium;
const formatJoinDate = formatTimestampDate;

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <Card>
      <div className="label-mono text-muted-foreground">{label}</div>
      <div className="font-display text-3xl mt-1 tabular-nums">{value}</div>
      {sub && (
        <div className="label-mono text-muted-foreground mt-1">{sub}</div>
      )}
    </Card>
  );
}

function StatStripSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <div className="h-3 w-20 bg-muted/60 rounded animate-pulse" />
          <div className="h-8 w-24 bg-muted/60 rounded mt-2 animate-pulse" />
        </Card>
      ))}
    </div>
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

function CardSkeleton({ heightClass = 'h-32' }: { heightClass?: string }) {
  return (
    <Card>
      <div className={`${heightClass} bg-muted/40 rounded animate-pulse`} />
    </Card>
  );
}

function NotFoundView({ username }: { username: string }) {
  return (
    <div className="space-y-4">
      <Card>
        <h1 className="text-2xl font-semibold tracking-tight">
          No one named {username}
        </h1>
        <p className="text-muted-foreground text-sm mt-2">
          That profile doesn't exist. Check the spelling, or head back to the
          feed.
        </p>
        <Button variant="primary" className="mt-4" to="/feed">
          Back to feed
        </Button>
      </Card>
    </div>
  );
}

function ErrorView({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : 'Could not load this profile.';
  return (
    <Card className="border-destructive/40 bg-destructive/5">
      <p className="text-destructive text-sm">{message}</p>
      <Button variant="secondary" className="mt-3" onClick={onRetry}>
        Try again
      </Button>
    </Card>
  );
}

function Header({
  username,
  joinDate,
}: {
  username: string;
  joinDate?: string;
}) {
  return (
    <div>
      <h1 className="font-display text-4xl tracking-tight">{username}</h1>
      {joinDate && (
        <p className="text-muted-foreground text-sm mt-1">
          Joined {formatJoinDate(joinDate)}
        </p>
      )}
    </div>
  );
}

function StatStrip({ data }: { data: UserSummaryResponse }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <StatCard
        label="All-time steps"
        value={formatNumber(data.total_steps_all_time)}
      />
      <StatCard
        label="Days active"
        value={formatNumber(data.days_active)}
      />
      <StatCard
        label="All-time rank"
        value={data.rank_all_time !== null ? `#${data.rank_all_time}` : '—'}
      />
      <StatCard
        label="Best day"
        value={data.best_day ? formatNumber(data.best_day.total) : '—'}
        sub={data.best_day ? formatHeadingDate(data.best_day.date) : undefined}
      />
    </div>
  );
}

function ThisWeekCard({ data }: { data: UserWeeklyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="font-display text-2xl tracking-tight">This week</h2>
        <span className="label-mono text-muted-foreground">
          {formatNumber(data.weekly_total)} steps ·{' '}
          {data.rank_this_week !== null ? `#${data.rank_this_week}` : '—'}
        </span>
      </div>
      <WeeklyBars days={data.daily_breakdown} />
    </Card>
  );
}

function TodayCard({ data }: { data: UserDailyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-display text-2xl tracking-tight">Today</h2>
        <span className="label-mono text-muted-foreground">
          {data.rank_today !== null ? `#${data.rank_today}` : '—'}
        </span>
      </div>
      <div className="font-display text-4xl mt-2 tabular-nums">
        {formatNumber(data.total)}
      </div>
      <div className="label-mono text-muted-foreground mt-1">
        {data.posts.length === 0
          ? 'No posts yet today.'
          : `${data.posts.length} ${data.posts.length === 1 ? 'snapshot' : 'snapshots'}`}
      </div>
    </Card>
  );
}

export default function Profile() {
  const { username = '' } = useParams<{ username: string }>();

  const summary = useQuery({
    queryKey: ['steps', 'users', username, 'summary'],
    queryFn: () => getUserSummary(username),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });

  const weekly = useQuery({
    queryKey: ['steps', 'users', username, 'weekly'],
    queryFn: () => getUserWeekly(username),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });

  const today = currentDate();
  const daily = useQuery({
    queryKey: ['steps', 'users', username, 'daily', today],
    queryFn: () => getUserDaily(username, today),
    enabled: !!username,
    staleTime: 30_000,
    retry: false,
  });

  // 404 detection lives on the summary query — the per-endpoint code
  // is identical across all three, but summary is the canonical
  // "this user exists" check.
  if (
    summary.error instanceof ApiError &&
    summary.error.code === 'user_not_found'
  ) {
    return <NotFoundView username={username} />;
  }

  if (summary.isPending) {
    return (
      <div className="space-y-6">
        <Header username={username} />
        <StatStripSkeleton />
        <CardSkeleton heightClass="h-32" />
        <CardSkeleton heightClass="h-20" />
      </div>
    );
  }

  if (summary.isError) {
    return (
      <div className="space-y-6">
        <Header username={username} />
        <ErrorView error={summary.error} onRetry={() => summary.refetch()} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Header username={summary.data.username} joinDate={summary.data.join_date} />
      <StatStrip data={summary.data} />
      {weekly.isPending ? (
        <CardSkeleton heightClass="h-32" />
      ) : weekly.isError ? (
        <ErrorView error={weekly.error} onRetry={() => weekly.refetch()} />
      ) : (
        <ThisWeekCard data={weekly.data} />
      )}
      {daily.isPending ? (
        <CardSkeleton heightClass="h-20" />
      ) : daily.isError ? (
        <ErrorView error={daily.error} onRetry={() => daily.refetch()} />
      ) : (
        <TodayCard data={daily.data} />
      )}
      <div className="pt-2">
        <Link
          to="/feed"
          className="label-mono text-muted-foreground hover:text-foreground border-b border-transparent hover:border-foreground transition-colors pb-0.5"
        >
          ← back to feed
        </Link>
      </div>
    </div>
  );
}
