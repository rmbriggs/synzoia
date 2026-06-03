import { describe, expect, it } from 'vitest';

import { averagePerLoggedDay } from '@/lib/stats';

describe('averagePerLoggedDay', () => {
  it('averages over only the days that have data (ignores empty days)', () => {
    // 431 + 438 + 432 = 1301 over 3 logged days -> 433.67 -> 434 (= 7h 14m)
    expect(
      averagePerLoggedDay([
        { total: 0 },
        { total: 0 },
        { total: 0 },
        { total: 0 },
        { total: 431 },
        { total: 438 },
        { total: 432 },
      ]),
    ).toBe(434);
  });

  it('returns 0 when no day has data', () => {
    expect(averagePerLoggedDay([{ total: 0 }, { total: 0 }])).toBe(0);
    expect(averagePerLoggedDay([])).toBe(0);
  });

  it('returns the value itself for a single logged day', () => {
    expect(averagePerLoggedDay([{ total: 0 }, { total: 500 }])).toBe(500);
  });
});
