import { describe, expect, it } from 'vitest';
import { groupPostsByDay } from '@/lib/feedGroups';
import type { FeedPost } from '@/api/posts';

const now = new Date('2026-05-29T18:00:00Z');

function post(id: number, iso: string): FeedPost {
  return {
    id,
    user_id: 1,
    username: 'u',
    type: 'steps',
    timestamp: iso,
    details: null,
    body: null,
  };
}

describe('groupPostsByDay', () => {
  it('splits posts into day groups, newest-first, preserving order', () => {
    const groups = groupPostsByDay(
      [
        post(1, '2026-05-29T20:00:00Z'),
        post(2, '2026-05-29T14:00:00Z'),
        post(3, '2026-05-28T14:00:00Z'),
        post(4, '2026-05-27T14:00:00Z'),
      ],
      now,
    );

    expect(groups.map((g) => g.label)).toEqual([
      'Today',
      'Yesterday',
      'Wednesday, May 27',
    ]);
    expect(groups[0].posts.map((p) => p.id)).toEqual([1, 2]);
    expect(groups[1].posts.map((p) => p.id)).toEqual([3]);
    expect(groups[2].posts.map((p) => p.id)).toEqual([4]);
    expect(groups[0].key).toBe('2026-05-29');
  });

  it('returns a single group when all posts share a day', () => {
    const groups = groupPostsByDay(
      [post(1, '2026-05-29T20:00:00Z'), post(2, '2026-05-29T08:00:00Z')],
      now,
    );
    expect(groups).toHaveLength(1);
    expect(groups[0].posts).toHaveLength(2);
  });

  it('returns [] for an empty feed', () => {
    expect(groupPostsByDay([], now)).toEqual([]);
  });
});
