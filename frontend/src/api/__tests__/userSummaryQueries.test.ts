import { describe, expect, it } from 'vitest';

import { userSummaryQueries, userFeedQuery } from '@/api/userSummaryQueries';

describe('userSummaryQueries', () => {
  it('produces the 8 Summary query keys Profile uses', () => {
    const keys = userSummaryQueries('alice', '2026-06-01', '2026-06').map(
      (q) => q.queryKey,
    );
    expect(keys).toEqual([
      ['steps', 'users', 'alice', 'summary'],
      ['steps', 'users', 'alice', 'daily', '2026-06-01'],
      ['steps', 'users', 'alice', 'weekly'],
      ['steps', 'users', 'alice', 'monthly', '2026-06'],
      ['sleep', 'users', 'alice', 'summary'],
      ['sleep', 'users', 'alice', 'daily', '2026-06-01'],
      ['sleep', 'users', 'alice', 'weekly'],
      ['sleep', 'users', 'alice', 'monthly', '2026-06'],
    ]);
  });

  it('each query has a callable queryFn and no-retry options', () => {
    for (const q of userSummaryQueries('bob', '2026-06-01', '2026-06')) {
      expect(typeof q.queryFn).toBe('function');
      expect(q.staleTime).toBe(30_000);
      expect(q.retry).toBe(false);
    }
  });
});

describe('userFeedQuery', () => {
  it('matches the FeedPanel query key and options', () => {
    const q = userFeedQuery('alice');
    expect(q.queryKey).toEqual(['posts', 'users', 'alice', 'feed', 50]);
    expect(q.staleTime).toBe(30_000);
    expect(typeof q.queryFn).toBe('function');
    // Intentionally NOT set — FeedPanel uses the default retry, unlike
    // the summary builders. Pinning this prevents an accidental change.
    expect('retry' in q).toBe(false);
  });
});
