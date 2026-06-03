import { describe, expect, it } from 'vitest';
import {
  ctDayKey,
  currentDate,
  currentMonthYYYYMM,
  formatDayHeader,
  formatDuration,
  lastNightDate,
} from '@/lib/dates';

describe('currentMonthYYYYMM', () => {
  it('returns the YYYY-MM prefix of the CT current date', () => {
    expect(currentMonthYYYYMM()).toBe(currentDate().slice(0, 7));
  });

  it('matches the YYYY-MM shape', () => {
    expect(currentMonthYYYYMM()).toMatch(/^\d{4}-\d{2}$/);
  });
});

describe('formatDuration', () => {
  it('formats minutes as "Xh Ym"', () => {
    expect(formatDuration(452)).toBe('7h 32m');
  });

  it('handles whole hours', () => {
    expect(formatDuration(480)).toBe('8h 0m');
  });

  it('handles zero', () => {
    expect(formatDuration(0)).toBe('0h 0m');
  });

  it('handles sub-hour durations', () => {
    expect(formatDuration(45)).toBe('0h 45m');
  });
});

describe('ctDayKey', () => {
  it('returns the CT calendar day (YYYY-MM-DD) of a UTC timestamp', () => {
    expect(ctDayKey('2026-05-27T15:00:00Z')).toBe('2026-05-27');
  });
});

describe('formatDayHeader', () => {
  const now = new Date('2026-05-29T18:00:00Z'); // ~1pm CT, 2026-05-29

  it('labels the current CT day "Today"', () => {
    expect(formatDayHeader('2026-05-29T18:00:00Z', now)).toBe('Today');
  });

  it('labels the prior CT day "Yesterday"', () => {
    expect(formatDayHeader('2026-05-28T18:00:00Z', now)).toBe('Yesterday');
  });

  it('labels older days as "Weekday, Month Day"', () => {
    expect(formatDayHeader('2026-05-27T15:00:00Z', now)).toBe('Wednesday, May 27');
  });
});

describe('lastNightDate', () => {
  it('is the CT day before today (the night_of you woke from this morning)', () => {
    const now = new Date('2026-06-02T18:00:00Z'); // ~1pm CT, 2026-06-02
    expect(lastNightDate(now)).toBe('2026-06-01');
  });

  it('matches YYYY-MM-DD shape', () => {
    expect(lastNightDate()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
