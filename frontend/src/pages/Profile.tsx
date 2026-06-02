import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import DailyBars from '@/components/ui/DailyBars';
import EmptyState from '@/components/ui/EmptyState';
import ErrorCard from '@/components/ui/ErrorCard';
import TabStrip from '@/components/ui/TabStrip';
import FeedSkeleton from '@/components/feed/FeedSkeleton';
import GenericPost from '@/components/feed/GenericPost';
import MilestonePost from '@/components/feed/MilestonePost';
import RecapPost from '@/components/feed/RecapPost';
import SleepPost from '@/components/feed/SleepPost';
import { ApiError } from '@/api/client';
import { type FeedPost } from '@/api/posts';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import type {
  UserDailyResponse,
  UserMonthlyResponse,
  UserSummaryResponse,
  UserWeeklyResponse,
} from '@/api/steps';
import type {
  UserDailyResponse as SleepDailyResponse,
  UserWeeklyResponse as SleepWeeklyResponse,
  UserMonthlyResponse as SleepMonthlyResponse,
  UserSummaryResponse as SleepSummaryResponse,
} from '@/api/sleep';
import {
  stepsSummaryQuery,
  stepsDailyQuery,
  stepsWeeklyQuery,
  stepsMonthlyQuery,
  sleepSummaryQuery,
  sleepDailyQuery,
  sleepWeeklyQuery,
  sleepMonthlyQuery,
  userFeedQuery,
} from '@/api/userSummaryQueries';
import {
  currentDate,
  currentMonthYYYYMM,
  formatDateMedium,
  formatDuration,
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
      <DailyBars days={data.daily_breakdown} cols={7} />
    </Card>
  );
}

function ThisMonthCard({ data }: { data: UserMonthlyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="font-display text-2xl tracking-tight">This month</h2>
        <span className="label-mono text-muted-foreground">
          {formatNumber(data.monthly_total)} steps ·{' '}
          {data.rank_this_month !== null ? `#${data.rank_this_month}` : '—'}
        </span>
      </div>
      {data.daily_breakdown.length === 0 ? (
        <div className="label-mono text-muted-foreground italic">
          No activity this month yet.
        </div>
      ) : (
        <DailyBars days={data.daily_breakdown} />
      )}
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

function formatSleepHours(minutes: number): string {
  // Floor (not round) so an all-time total reads as whole hours actually
  // accumulated — matches formatDuration's hours component, and a single
  // 58-minute night shows "0h", not a misleading "1h".
  return `${Math.floor(minutes / 60)}h`;
}

function SleepStatStrip({ data }: { data: SleepSummaryResponse }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <StatCard
        label="All-time sleep"
        value={formatSleepHours(data.total_minutes_all_time)}
      />
      <StatCard label="Nights logged" value={formatNumber(data.nights_logged)} />
      <StatCard
        label="All-time rank"
        value={data.rank_all_time !== null ? `#${data.rank_all_time}` : '—'}
      />
      <StatCard
        label="Best night"
        value={data.best_night ? formatDuration(data.best_night.total) : '—'}
        sub={
          data.best_night ? formatHeadingDate(data.best_night.date) : undefined
        }
      />
    </div>
  );
}

function SleepTodayCard({ data }: { data: SleepDailyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-display text-2xl tracking-tight">Last night</h2>
        <span className="label-mono text-muted-foreground">
          {data.rank_today !== null ? `#${data.rank_today}` : '—'}
        </span>
      </div>
      <div className="font-display text-4xl mt-2 tabular-nums">
        {data.total > 0 ? formatDuration(data.total) : '—'}
      </div>
      <div className="label-mono text-muted-foreground mt-1">
        {data.post === null ? 'No sleep logged.' : 'Logged'}
      </div>
    </Card>
  );
}

function SleepThisWeekCard({ data }: { data: SleepWeeklyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="font-display text-2xl tracking-tight">This week</h2>
        <span className="label-mono text-muted-foreground">
          {formatDuration(data.weekly_total)} ·{' '}
          {data.rank_this_week !== null ? `#${data.rank_this_week}` : '—'}
        </span>
      </div>
      <DailyBars
        days={data.daily_breakdown}
        cols={7}
        formatValue={formatDuration}
        unit=""
      />
    </Card>
  );
}

function SleepThisMonthCard({ data }: { data: SleepMonthlyResponse }) {
  return (
    <Card>
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="font-display text-2xl tracking-tight">This month</h2>
        <span className="label-mono text-muted-foreground">
          {formatDuration(data.monthly_total)} ·{' '}
          {data.rank_this_month !== null ? `#${data.rank_this_month}` : '—'}
        </span>
      </div>
      {data.daily_breakdown.length === 0 ? (
        <div className="label-mono text-muted-foreground italic">
          No sleep this month yet.
        </div>
      ) : (
        <DailyBars
          days={data.daily_breakdown}
          formatValue={formatDuration}
          unit=""
        />
      )}
    </Card>
  );
}

const TABS = [
  { key: 'summary', label: 'Summary' },
  { key: 'feed', label: 'Feed' },
] as const;

function SummaryPanel({ username }: { username: string }) {
  const today = currentDate();
  const month = currentMonthYYYYMM();

  const summary = useQuery({ ...stepsSummaryQuery(username), enabled: !!username });
  const daily = useQuery({ ...stepsDailyQuery(username, today), enabled: !!username });
  const weekly = useQuery({ ...stepsWeeklyQuery(username), enabled: !!username });
  const monthly = useQuery({ ...stepsMonthlyQuery(username, month), enabled: !!username });

  const sleepSummary = useQuery({ ...sleepSummaryQuery(username), enabled: !!username });
  const sleepDaily = useQuery({ ...sleepDailyQuery(username, today), enabled: !!username });
  const sleepWeekly = useQuery({ ...sleepWeeklyQuery(username), enabled: !!username });
  const sleepMonthly = useQuery({ ...sleepMonthlyQuery(username, month), enabled: !!username });

  return (
    <div className="space-y-8">
      <section className="space-y-6">
        <h2 className="label-mono text-muted-foreground">Steps</h2>
        {summary.isPending ? (
          <StatStripSkeleton />
        ) : summary.isError ? (
          <ErrorView error={summary.error} onRetry={() => summary.refetch()} />
        ) : (
          <StatStrip data={summary.data} />
        )}

        {daily.isPending ? (
          <CardSkeleton heightClass="h-20" />
        ) : daily.isError ? (
          <ErrorView error={daily.error} onRetry={() => daily.refetch()} />
        ) : (
          <TodayCard data={daily.data} />
        )}

        {weekly.isPending ? (
          <CardSkeleton heightClass="h-32" />
        ) : weekly.isError ? (
          <ErrorView error={weekly.error} onRetry={() => weekly.refetch()} />
        ) : (
          <ThisWeekCard data={weekly.data} />
        )}

        {monthly.isPending ? (
          <CardSkeleton heightClass="h-32" />
        ) : monthly.isError ? (
          <ErrorView error={monthly.error} onRetry={() => monthly.refetch()} />
        ) : (
          <ThisMonthCard data={monthly.data} />
        )}
      </section>

      <section className="space-y-6">
        <h2 className="label-mono text-muted-foreground">Sleep</h2>
        {sleepSummary.isPending ? (
          <StatStripSkeleton />
        ) : sleepSummary.isError ? (
          <ErrorView
            error={sleepSummary.error}
            onRetry={() => sleepSummary.refetch()}
          />
        ) : (
          <SleepStatStrip data={sleepSummary.data} />
        )}

        {sleepDaily.isPending ? (
          <CardSkeleton heightClass="h-20" />
        ) : sleepDaily.isError ? (
          <ErrorView
            error={sleepDaily.error}
            onRetry={() => sleepDaily.refetch()}
          />
        ) : (
          <SleepTodayCard data={sleepDaily.data} />
        )}

        {sleepWeekly.isPending ? (
          <CardSkeleton heightClass="h-32" />
        ) : sleepWeekly.isError ? (
          <ErrorView
            error={sleepWeekly.error}
            onRetry={() => sleepWeekly.refetch()}
          />
        ) : (
          <SleepThisWeekCard data={sleepWeekly.data} />
        )}

        {sleepMonthly.isPending ? (
          <CardSkeleton heightClass="h-32" />
        ) : sleepMonthly.isError ? (
          <ErrorView
            error={sleepMonthly.error}
            onRetry={() => sleepMonthly.refetch()}
          />
        ) : (
          <SleepThisMonthCard data={sleepMonthly.data} />
        )}
      </section>
    </div>
  );
}

function FeedPanel({ username }: { username: string }) {
  const query = useQuery({ ...userFeedQuery(username), enabled: !!username });

  if (query.isPending) return <FeedSkeleton />;
  if (query.isError) {
    return (
      <ErrorCard
        error={query.error}
        onRetry={() => query.refetch()}
        fallbackMessage="Could not load this user's feed."
      />
    );
  }
  if (query.data.posts.length === 0) {
    return (
      <Card>
        <EmptyState message="No posts mention this user yet." />
      </Card>
    );
  }
  return (
    <div className="space-y-4">
      {query.data.posts.map((post: FeedPost) => {
        if (post.type === 'leaderboard_recap') return <RecapPost key={post.id} post={post} />;
        if (post.type === 'steps_milestone') return <MilestonePost key={post.id} post={post} />;
        if (post.type === 'sleep') return <SleepPost key={post.id} post={post} />;
        return <GenericPost key={post.id} post={post} />;
      })}
    </div>
  );
}

export default function Profile() {
  const { username = '' } = useParams<{ username: string }>();
  const [params] = useSearchParams();
  const active = params.get('tab') ?? 'summary';

  // 404 detection hangs on the summary query because every Profile
  // visit hits it regardless of which tab is active. React Query
  // dedupes by queryKey, so the inner SummaryPanel's summary query
  // shares this network request.
  const summary = useQuery({ ...stepsSummaryQuery(username), enabled: !!username });

  const { currentUser, setCurrentUser } = useCurrentUser();

  const queryClient = useQueryClient();
  // Warm the feed in the background as soon as the profile loads, so the
  // Feed tab renders instantly when opened. prefetchQuery respects
  // staleTime and swallows errors, so this never affects the Summary view.
  useEffect(() => {
    if (username) queryClient.prefetchQuery(userFeedQuery(username));
  }, [queryClient, username]);

  // Defensive guard for the unlikely case where useParams returns
  // empty — Profile is only routed under /u/:username, so this is
  // belt-and-suspenders against a route misconfig. Placed AFTER all
  // hooks to respect the Rules of Hooks.
  if (!username) {
    return <NotFoundView username="" />;
  }

  if (
    summary.error instanceof ApiError &&
    summary.error.code === 'user_not_found'
  ) {
    return <NotFoundView username={username} />;
  }

  return (
    <div className="space-y-6">
      <Header
        username={summary.data?.username ?? username}
        joinDate={summary.data?.join_date}
      />
      {currentUser === username ? (
        <Button variant="secondary" disabled>
          ✓ This is you
        </Button>
      ) : (
        <Button variant="primary" onClick={() => setCurrentUser(username)}>
          Make this me
        </Button>
      )}
      <TabStrip tabs={[...TABS]} defaultKey="summary" />
      {active === 'feed' ? (
        <FeedPanel username={username} />
      ) : (
        <SummaryPanel username={username} />
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
