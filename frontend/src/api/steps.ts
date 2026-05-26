import { apiFetch } from './client';

export interface LeaderboardEntry {
  rank: number;
  username: string;
  total: number;
}

export interface DailyTotal {
  date: string;
  total: number;
}

export interface GlobalDailyResponse {
  date: string;
  total_steps: number;
  participating_users: number;
  leaderboard: LeaderboardEntry[];
}

export interface GlobalWeeklyResponse {
  week_start: string;
  week_end: string;
  total_steps: number;
  leaderboard: LeaderboardEntry[];
  daily_breakdown: DailyTotal[];
}

export interface SummaryLeader {
  username: string;
  total: number;
}

export interface BestDayEver {
  date: string;
  total: number;
  username: string;
}

export interface GlobalSummaryResponse {
  total_users: number;
  total_steps_all_time: number;
  today_leader: SummaryLeader | null;
  this_week_leader: SummaryLeader | null;
  best_day_ever: BestDayEver | null;
}

export interface StepPost {
  timestamp: string;
  total: number;
}

export interface UserDailyResponse {
  username: string;
  date: string;
  total: number;
  rank_today: number | null;
  posts: StepPost[];
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

export interface UserBestDay {
  date: string;
  total: number;
}

export interface UserSummaryResponse {
  username: string;
  join_date: string;
  total_steps_all_time: number;
  best_day: UserBestDay | null;
  rank_all_time: number | null;
  days_active: number;
}

export function getGlobalDaily(date?: string): Promise<GlobalDailyResponse> {
  const qs = date ? `?date=${encodeURIComponent(date)}` : '';
  return apiFetch<GlobalDailyResponse>(`/steps/daily${qs}`);
}

export function getGlobalWeekly(
  weekStart?: string,
): Promise<GlobalWeeklyResponse> {
  const qs = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : '';
  return apiFetch<GlobalWeeklyResponse>(`/steps/weekly${qs}`);
}

export function getGlobalSummary(): Promise<GlobalSummaryResponse> {
  return apiFetch<GlobalSummaryResponse>('/steps/summary');
}

export function getUserDaily(
  username: string,
  date?: string,
): Promise<UserDailyResponse> {
  const qs = date ? `?date=${encodeURIComponent(date)}` : '';
  return apiFetch<UserDailyResponse>(
    `/steps/users/${encodeURIComponent(username)}/daily${qs}`,
  );
}

export function getUserWeekly(
  username: string,
  weekStart?: string,
): Promise<UserWeeklyResponse> {
  const qs = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : '';
  return apiFetch<UserWeeklyResponse>(
    `/steps/users/${encodeURIComponent(username)}/weekly${qs}`,
  );
}

export function getUserMonthly(
  username: string,
  month?: string,
): Promise<UserMonthlyResponse> {
  const qs = month ? `?month=${encodeURIComponent(month)}` : '';
  return apiFetch<UserMonthlyResponse>(
    `/steps/users/${encodeURIComponent(username)}/monthly${qs}`,
  );
}

export function getUserSummary(username: string): Promise<UserSummaryResponse> {
  return apiFetch<UserSummaryResponse>(
    `/steps/users/${encodeURIComponent(username)}/summary`,
  );
}
