/**
 * Single source of truth for the per-user profile query builders (summary + feed).
 *
 * The Profile page (Summary tab) and the Users-list hover prefetch BOTH
 * use these builders, so their React Query keys are guaranteed identical
 * — otherwise a prefetch would warm cache entries the Profile page never
 * reads. `today` / `month` are passed in (from lib/dates) so the
 * date-stamped keys match across call sites.
 */
import {
  getUserSummary as getStepsSummary,
  getUserDaily as getStepsDaily,
  getUserWeekly as getStepsWeekly,
  getUserMonthly as getStepsMonthly,
} from '@/api/steps';
import {
  getUserSummary as getSleepSummary,
  getUserDaily as getSleepDaily,
  getUserWeekly as getSleepWeekly,
  getUserMonthly as getSleepMonthly,
} from '@/api/sleep';
import { getUserFeed } from '@/api/posts';
import type { FetchQueryOptions } from '@tanstack/react-query';

const STALE = 30_000;
const FEED_LIMIT = 50;

export const stepsSummaryQuery = (u: string) => ({
  queryKey: ['steps', 'users', u, 'summary'] as const,
  queryFn: () => getStepsSummary(u),
  staleTime: STALE,
  retry: false as const,
});

export const stepsDailyQuery = (u: string, today: string) => ({
  queryKey: ['steps', 'users', u, 'daily', today] as const,
  queryFn: () => getStepsDaily(u, today),
  staleTime: STALE,
  retry: false as const,
});

export const stepsWeeklyQuery = (u: string) => ({
  queryKey: ['steps', 'users', u, 'weekly'] as const,
  queryFn: () => getStepsWeekly(u),
  staleTime: STALE,
  retry: false as const,
});

export const stepsMonthlyQuery = (u: string, month: string) => ({
  queryKey: ['steps', 'users', u, 'monthly', month] as const,
  queryFn: () => getStepsMonthly(u, month),
  staleTime: STALE,
  retry: false as const,
});

export const sleepSummaryQuery = (u: string) => ({
  queryKey: ['sleep', 'users', u, 'summary'] as const,
  queryFn: () => getSleepSummary(u),
  staleTime: STALE,
  retry: false as const,
});

export const sleepDailyQuery = (u: string, today: string) => ({
  queryKey: ['sleep', 'users', u, 'daily', today] as const,
  queryFn: () => getSleepDaily(u, today),
  staleTime: STALE,
  retry: false as const,
});

export const sleepWeeklyQuery = (u: string) => ({
  queryKey: ['sleep', 'users', u, 'weekly'] as const,
  queryFn: () => getSleepWeekly(u),
  staleTime: STALE,
  retry: false as const,
});

export const sleepMonthlyQuery = (u: string, month: string) => ({
  queryKey: ['sleep', 'users', u, 'monthly', month] as const,
  queryFn: () => getSleepMonthly(u, month),
  staleTime: STALE,
  retry: false as const,
});

/**
 * The user's feed query (Profile's Feed tab). No `retry` override — it
 * mirrors FeedPanel's existing query, which uses the default retry
 * (the summary builders set retry:false; the feed one does not).
 */
export const userFeedQuery = (u: string) => ({
  queryKey: ['posts', 'users', u, 'feed', FEED_LIMIT] as const,
  queryFn: () => getUserFeed(u, FEED_LIMIT),
  staleTime: STALE,
});

/**
 * All 8 Summary-tab queries for a user, in display order. Typed as the
 * common `FetchQueryOptions` so the array is homogeneous and can be fed
 * straight to `queryClient.prefetchQuery` without a cast. The individual
 * builders above keep their precise per-query types for Profile's
 * `useQuery` call sites.
 */
export function userSummaryQueries(
  u: string,
  today: string,
  month: string,
): FetchQueryOptions[] {
  return [
    stepsSummaryQuery(u),
    stepsDailyQuery(u, today),
    stepsWeeklyQuery(u),
    stepsMonthlyQuery(u, month),
    sleepSummaryQuery(u),
    sleepDailyQuery(u, today),
    sleepWeeklyQuery(u),
    sleepMonthlyQuery(u, month),
  ];
}
