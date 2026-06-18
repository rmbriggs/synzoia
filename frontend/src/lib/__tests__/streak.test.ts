import { describe, it, expect } from 'vitest';
import { currentStreak } from '@/lib/streak';

describe('currentStreak', () => {
  it('counts consecutive days ending today with steps > 0', () => {
    const days = [
      { date: '2026-06-16', total: 8000 },
      { date: '2026-06-17', total: 12000 },
      { date: '2026-06-18', total: 9000 },
    ];
    expect(currentStreak(days, '2026-06-18')).toBe(3);
  });
  it('breaks on a zero or missing day', () => {
    const days = [
      { date: '2026-06-16', total: 8000 },
      { date: '2026-06-17', total: 0 },
      { date: '2026-06-18', total: 9000 },
    ];
    expect(currentStreak(days, '2026-06-18')).toBe(1);
  });
  it('is 0 when today has no steps', () => {
    expect(currentStreak([{ date: '2026-06-17', total: 8000 }], '2026-06-18')).toBe(0);
  });
});
