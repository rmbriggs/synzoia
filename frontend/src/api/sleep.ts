import { apiFetch } from './client';

export interface DailyTotal {
  date: string;
  total: number; // minutes
}

export interface SleepPostDetail {
  night_of: string;
  bedtime: string;
  wake_time: string;
  duration_min: number;
  rem_minutes: number | null;
  core_minutes: number | null;
  deep_minutes: number | null;
  awake_minutes: number | null;
}

export interface UserDailyResponse {
  username: string;
  date: string;
  total: number; // duration_min for that night
  rank_today: number | null;
  post: SleepPostDetail | null;
}

export interface UserWeeklyResponse {
  username: string;
  week_start: string;
  week_end: string;
  weekly_total: number;
  rank_this_week: number | null;
  daily_breakdown: DailyTotal[];
}

export interface UserMonthlyResponse {
  username: string;
  month_start: string;
  month_end: string;
  monthly_total: number;
  rank_this_month: number | null;
  daily_breakdown: DailyTotal[];
}

export interface UserBestNight {
  date: string;
  total: number;
}

export interface UserSummaryResponse {
  username: string;
  join_date: string;
  score: number;
  best_night: UserBestNight | null;
  rank: number | null;
}

export function getUserDaily(
  username: string,
  date?: string,
): Promise<UserDailyResponse> {
  const qs = date ? `?date=${encodeURIComponent(date)}` : '';
  return apiFetch<UserDailyResponse>(
    `/sleep/users/${encodeURIComponent(username)}/daily${qs}`,
  );
}

export function getUserWeekly(
  username: string,
  asOf?: string,
): Promise<UserWeeklyResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return apiFetch<UserWeeklyResponse>(
    `/sleep/users/${encodeURIComponent(username)}/weekly${qs}`,
  );
}

export function getUserMonthly(
  username: string,
  asOf?: string,
): Promise<UserMonthlyResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return apiFetch<UserMonthlyResponse>(
    `/sleep/users/${encodeURIComponent(username)}/monthly${qs}`,
  );
}

export function getUserSummary(username: string): Promise<UserSummaryResponse> {
  return apiFetch<UserSummaryResponse>(
    `/sleep/users/${encodeURIComponent(username)}/summary`,
  );
}

export interface GlobalSleepSummaryResponse {
  total_users: number;
  total_minutes_all_time: number;
  today_leader: { username: string; total: number } | null;
  this_week_leader: { username: string; total: number } | null;
  best_night_ever: { date: string; total: number; username: string } | null;
}

export function getGlobalSleepSummary(): Promise<GlobalSleepSummaryResponse> {
  return apiFetch<GlobalSleepSummaryResponse>('/sleep/summary');
}
