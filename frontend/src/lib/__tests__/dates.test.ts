import { describe, expect, it } from 'vitest';
import { formatDuration } from '@/lib/dates';

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
