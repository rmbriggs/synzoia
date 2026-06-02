import type { FeedPost } from '@/api/posts';
import { ctDayKey, formatDayHeader } from '@/lib/dates';

export interface DayGroup {
  key: string;
  label: string;
  posts: FeedPost[];
}

/**
 * Split an already-ordered feed into consecutive day groups. The server
 * returns posts newest-first, so groups come out newest-day-first and a
 * single pass (grouping consecutive same-day posts) fully groups them.
 */
export function groupPostsByDay(
  posts: FeedPost[],
  now: Date = new Date(),
): DayGroup[] {
  const groups: DayGroup[] = [];
  for (const post of posts) {
    const key = ctDayKey(post.timestamp);
    const last = groups[groups.length - 1];
    if (last && last.key === key) {
      last.posts.push(post);
    } else {
      groups.push({ key, label: formatDayHeader(post.timestamp, now), posts: [post] });
    }
  }
  return groups;
}
