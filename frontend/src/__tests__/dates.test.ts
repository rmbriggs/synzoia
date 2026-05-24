import { describe, expect, it } from 'vitest';
import { formatRelative } from '@/lib/dates';

describe('formatRelative', () => {
  const now = new Date('2026-05-24T15:00:00Z'); // 10am CT

  it('returns "just now" within the same minute', () => {
    const just = new Date('2026-05-24T14:59:45Z').toISOString();
    expect(formatRelative(just, now)).toBe('just now');
  });

  it('returns "Nm ago" for less than an hour', () => {
    const fifteenMin = new Date('2026-05-24T14:45:00Z').toISOString();
    expect(formatRelative(fifteenMin, now)).toBe('15m ago');
  });

  it('returns "Nh ago" for less than a day', () => {
    const threeH = new Date('2026-05-24T12:00:00Z').toISOString();
    expect(formatRelative(threeH, now)).toBe('3h ago');
  });

  it('returns "yesterday" for the previous CT day', () => {
    // 2026-05-24T01:00:00Z = 2026-05-23 20:00 CT (yesterday in CT)
    const yesterdayCT = new Date('2026-05-24T01:00:00Z').toISOString();
    expect(formatRelative(yesterdayCT, now)).toBe('yesterday');
  });

  it('returns a "Month Day" string for older posts', () => {
    const old = new Date('2026-05-21T15:00:00Z').toISOString();
    expect(formatRelative(old, now)).toMatch(/May 21/);
  });
});
