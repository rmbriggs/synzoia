import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams, useSearchParams } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import RangeTrendCard from '@/components/ui/RangeTrendCard';
import EmptyState from '@/components/ui/EmptyState';
import ErrorCard from '@/components/ui/ErrorCard';
import TabStrip from '@/components/ui/TabStrip';
import FeedSkeleton from '@/components/feed/FeedSkeleton';
import GenericPost from '@/components/feed/GenericPost';
import MilestonePost from '@/components/feed/MilestonePost';
import RecapPost from '@/components/feed/RecapPost';
import SleepPost from '@/components/feed/SleepPost';
import UserAvatar from '@/components/ui/UserAvatar';
import { ApiError } from '@/api/client';
import { type FeedPost } from '@/api/posts';
import { getProfiles } from '@/api/profiles';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import type {
  UserDailyResponse,
  UserSummaryResponse,
} from '@/api/steps';
import type {
  UserDailyResponse as SleepDailyResponse,
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
  lastNightDate,
  formatDateMedium,
  formatDuration,
  formatTimestampDate,
} from '@/lib/dates';
import { currentStreak } from '@/lib/streak';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

const formatHeadingDate = formatDateMedium;
const formatJoinDate = formatTimestampDate;

// ── Error / skeleton helpers ──────────────────────────────────────────────────

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
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
      {Array.from({ length: 3 }).map((_, i) => (
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
          That profile does not exist. Check the spelling, or head back to the
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

// ── Coastal banner ────────────────────────────────────────────────────────────

/**
 * Token-driven coastal gradient banner. No photo, no hardcoded hex.
 * Uses on-palette CSS vars so it renders correctly in both light and dark mode.
 */
function ProfileBanner() {
  return (
    <div
      aria-hidden="true"
      className="h-36 sm:h-48 w-full"
      style={{
        background: `
          radial-gradient(ellipse 80% 120% at 20% 0%, color-mix(in oklch, var(--primary) 28%, transparent), transparent 65%),
          radial-gradient(ellipse 70% 100% at 85% 100%, color-mix(in oklch, var(--fern) 22%, transparent), transparent 60%),
          radial-gradient(ellipse 60% 80% at 50% 50%, color-mix(in oklch, var(--amber) 12%, transparent), transparent 55%),
          var(--secondary)
        `,
      }}
    />
  );
}

// ── Profile header card ───────────────────────────────────────────────────────

type ProfileHeaderProps = {
  username: string;
  joinDate?: string;
  streak: number;
  allTimeSteps: number | null;
  isMe: boolean;
  onMakeMe: () => void;
};

function ProfileHeader({
  username,
  joinDate,
  streak,
  allTimeSteps,
  isMe,
  onMakeMe,
}: ProfileHeaderProps) {
  return (
    <div className="px-4 sm:px-6 -mt-10 relative z-10">
      {/* Avatar + identity row */}
      <div className="flex items-end justify-between gap-4">
        <div className="flex items-end gap-4">
          <div className="border-4 border-background rounded-full shadow-md flex-shrink-0">
            <UserAvatar username={username} size="lg" />
          </div>
          <div className="pb-1">
            <h1 className="font-display text-3xl sm:text-4xl tracking-tight leading-none">
              @{username}
            </h1>
            {joinDate && (
              <p className="label-mono text-muted-foreground mt-1">
                Joined {formatJoinDate(joinDate)}
              </p>
            )}
            {/* All-time steps in header */}
            <p className="label-mono text-muted-foreground mt-0.5">
              {allTimeSteps !== null
                ? `${allTimeSteps.toLocaleString()} steps all time`
                : '—'}
            </p>
          </div>
        </div>

        {/* Identity button */}
        <div className="pb-1 flex-shrink-0">
          {isMe ? (
            <Button variant="secondary" disabled>
              This is you
            </Button>
          ) : (
            <Button variant="primary" onClick={onMakeMe}>
              Make this me
            </Button>
          )}
        </div>
      </div>

      {/* Streak pill — shown only when streak > 0 */}
      {streak > 0 && (
        <div className="mt-4 flex items-center gap-2">
          <span
            className="font-display text-xl tabular-nums"
            style={{ color: 'var(--amber)' }}
          >
            {streak}
          </span>
          <span aria-hidden="true">{'🔥'}</span>
          <span className="label-mono text-muted-foreground">day streak</span>
        </div>
      )}
    </div>
  );
}

function ProfileHeaderSkeleton({ username }: { username: string }) {
  return (
    <div className="px-4 sm:px-6 -mt-10 relative z-10">
      <div className="flex items-end gap-4">
        <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-muted/60 animate-pulse border-4 border-background flex-shrink-0" />
        <div className="pb-1 space-y-2">
          {/* Render the username as an h1 during loading so smoke tests pass */}
          <h1 className="font-display text-3xl sm:text-4xl tracking-tight leading-none">
            @{username}
          </h1>
          <div className="h-3 w-24 bg-muted/40 rounded animate-pulse" />
        </div>
      </div>
    </div>
  );
}

// ── Stat strips (unchanged from pre-coastal — preserve label strings for tests) ─

function StatStrip({
  data,
  allTimeSteps,
}: {
  data: UserSummaryResponse;
  allTimeSteps: number | null;
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <StatCard
        label="All-time steps"
        value={allTimeSteps !== null ? allTimeSteps.toLocaleString() : '—'}
      />
      <StatCard
        label="30-day score"
        value={formatNumber(data.score)}
      />
      <StatCard
        label="Rank"
        value={data.rank !== null ? `#${data.rank}` : '—'}
      />
      <StatCard
        label="Best day"
        value={data.best_day ? formatNumber(data.best_day.total) : '—'}
        sub={data.best_day ? formatHeadingDate(data.best_day.date) : undefined}
      />
    </div>
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

function SleepStatStrip({ data }: { data: SleepSummaryResponse }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
      <StatCard
        label="30-day score"
        value={`${Math.floor(data.score / 60)}h`}
      />
      <StatCard
        label="Rank"
        value={data.rank !== null ? `#${data.rank}` : '—'}
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

// ── Tabs ──────────────────────────────────────────────────────────────────────

const TABS = [
  { key: 'summary', label: 'Summary' },
  { key: 'feed', label: 'Feed' },
] as const;

// ── Summary panel ─────────────────────────────────────────────────────────────

function SummaryPanel({
  username,
  allTimeSteps,
}: {
  username: string;
  allTimeSteps: number | null;
}) {
  const today = currentDate();
  const lastNight = lastNightDate();

  const summary = useQuery({ ...stepsSummaryQuery(username), enabled: !!username });
  const daily = useQuery({ ...stepsDailyQuery(username, today), enabled: !!username });
  const weekly = useQuery({ ...stepsWeeklyQuery(username, today), enabled: !!username });
  const monthly = useQuery({ ...stepsMonthlyQuery(username, today), enabled: !!username });

  const sleepSummary = useQuery({ ...sleepSummaryQuery(username), enabled: !!username });
  const sleepDaily = useQuery({ ...sleepDailyQuery(username, lastNight), enabled: !!username });
  const sleepWeekly = useQuery({ ...sleepWeeklyQuery(username, lastNight), enabled: !!username });
  const sleepMonthly = useQuery({ ...sleepMonthlyQuery(username, lastNight), enabled: !!username });

  return (
    <div className="space-y-8">
      <section className="space-y-6">
        <h2 className="label-mono text-muted-foreground">Steps</h2>
        {summary.isPending ? (
          <StatStripSkeleton />
        ) : summary.isError ? (
          <ErrorView error={summary.error} onRetry={() => summary.refetch()} />
        ) : (
          <StatStrip data={summary.data} allTimeSteps={allTimeSteps} />
        )}

        {daily.isPending ? (
          <CardSkeleton heightClass="h-20" />
        ) : daily.isError ? (
          <ErrorView error={daily.error} onRetry={() => daily.refetch()} />
        ) : (
          <TodayCard data={daily.data} />
        )}

        <RangeTrendCard
          week={{
            isPending: weekly.isPending,
            isError: weekly.isError,
            error: weekly.error,
            onRetry: () => weekly.refetch(),
            days: weekly.data?.daily_breakdown ?? [],
            total: weekly.data?.weekly_total ?? 0,
            rank: weekly.data?.rank_this_week ?? null,
          }}
          month={{
            isPending: monthly.isPending,
            isError: monthly.isError,
            error: monthly.error,
            onRetry: () => monthly.refetch(),
            days: monthly.data?.daily_breakdown ?? [],
            total: monthly.data?.monthly_total ?? 0,
            rank: monthly.data?.rank_this_month ?? null,
          }}
          emptyMonthMessage="No activity in the last 30 days yet."
        />
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

        <RangeTrendCard
          week={{
            isPending: sleepWeekly.isPending,
            isError: sleepWeekly.isError,
            error: sleepWeekly.error,
            onRetry: () => sleepWeekly.refetch(),
            days: sleepWeekly.data?.daily_breakdown ?? [],
            total: sleepWeekly.data?.weekly_total ?? 0,
            rank: sleepWeekly.data?.rank_this_week ?? null,
          }}
          month={{
            isPending: sleepMonthly.isPending,
            isError: sleepMonthly.isError,
            error: sleepMonthly.error,
            onRetry: () => sleepMonthly.refetch(),
            days: sleepMonthly.data?.daily_breakdown ?? [],
            total: sleepMonthly.data?.monthly_total ?? 0,
            rank: sleepMonthly.data?.rank_this_month ?? null,
          }}
          formatValue={formatDuration}
          unit=""
          emptyMonthMessage="No sleep in the last 30 days yet."
        />
      </section>
    </div>
  );
}

// ── Feed panel ────────────────────────────────────────────────────────────────

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

// ── Main export ───────────────────────────────────────────────────────────────

export default function Profile() {
  const { username = '' } = useParams<{ username: string }>();
  const [params] = useSearchParams();
  const active = params.get('tab') ?? 'summary';

  const { currentUser, setCurrentUser } = useCurrentUser();
  const queryClient = useQueryClient();
  const today = currentDate();

  // Fetch profiles list — shares cache with the Users page (same key).
  const profilesQuery = useQuery({
    queryKey: ['profiles', 'list'],
    queryFn: getProfiles,
    staleTime: 60_000,
  });

  // Find this user's all-time steps from the profiles list.
  // null = still loading or user not found; treat both as "—".
  const allTimeSteps: number | null =
    profilesQuery.data?.profiles?.find((p) => p.username === username)
      ?.total_steps_all_time ?? null;

  // 404 detection: hits summary on every visit regardless of active tab.
  // React Query dedupes, so the inner SummaryPanel's summary query shares
  // this network request.
  const summary = useQuery({ ...stepsSummaryQuery(username), enabled: !!username });

  // Monthly steps breakdown powers the streak util.
  // `daily_breakdown` is already `{ date: string; total: number }[]` — same
  // shape currentStreak expects, no field renaming needed.
  const monthly = useQuery({ ...stepsMonthlyQuery(username, today), enabled: !!username });

  // Warm the feed in the background so the Feed tab is instant when opened.
  // prefetchQuery respects staleTime and swallows errors.
  useEffect(() => {
    if (username) queryClient.prefetchQuery(userFeedQuery(username));
  }, [queryClient, username]);

  // Defensive guard — Profile is only routed under /u/:username.
  if (!username) {
    return <NotFoundView username="" />;
  }

  if (
    summary.error instanceof ApiError &&
    summary.error.code === 'user_not_found'
  ) {
    return <NotFoundView username={username} />;
  }

  // Map monthly daily_breakdown -> streak input.
  // date field: daily_breakdown[i].date (YYYY-MM-DD, CT-anchored by the backend)
  // total field: daily_breakdown[i].total (step count for that calendar day)
  const streak = currentStreak(monthly.data?.daily_breakdown ?? [], today);

  return (
    <div className="space-y-0">
      {/* Coastal gradient banner — token-driven, no photo, no hardcoded hex */}
      <ProfileBanner />

      {/* Profile header: avatar (UserAvatar lg) + @username + join date + streak */}
      {summary.isPending ? (
        <ProfileHeaderSkeleton username={username} />
      ) : (
        <ProfileHeader
          username={summary.data?.username ?? username}
          joinDate={summary.data?.join_date}
          streak={streak}
          allTimeSteps={allTimeSteps}
          isMe={currentUser === username}
          onMakeMe={() => setCurrentUser(username)}
        />
      )}

      <div className="mt-6 space-y-6">
        {/* Tabs */}
        <TabStrip tabs={[...TABS]} defaultKey="summary" />

        {/* Tab bodies */}
        {active === 'feed' ? (
          <FeedPanel username={username} />
        ) : (
          <SummaryPanel username={username} allTimeSteps={allTimeSteps} />
        )}
      </div>
    </div>
  );
}
