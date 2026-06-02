import { describe, expect, it } from 'vitest';
import { currentDate, currentMonthYYYYMM, formatDuration } from '@/lib/dates';

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
