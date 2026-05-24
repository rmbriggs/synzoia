import { apiFetch } from './client';

export type PostType =
  | 'sleep'
  | 'steps'
  | 'workout'
  | 'steps_milestone'
  | 'leaderboard_recap';

export interface PostDetails {
  threshold?: number;
  date?: string;
  top?: { username: string; total: number }[];
}

export interface FeedPost {
  id: number;
  user_id: number;
  username: string;
  type: PostType;
  timestamp: string;
  details: PostDetails | null;
  body: string | null;
}

export interface FeedResponse {
  posts: FeedPost[];
}

export function getFeed(limit?: number): Promise<FeedResponse> {
  const qs = limit ? `?limit=${limit}` : '';
  return apiFetch<FeedResponse>(`/posts${qs}`);
}

export function getUserFeed(
  username: string,
  limit?: number,
): Promise<FeedResponse> {
  const qs = limit ? `?limit=${limit}` : '';
  return apiFetch<FeedResponse>(
    `/posts/users/${encodeURIComponent(username)}${qs}`,
  );
}
