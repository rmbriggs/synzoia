import { describe, expect, it } from 'vitest';
import { formatPostedAt } from '@/lib/dates';

describe('formatPostedAt', () => {
  // Anchor "now" to 10:00 AM CT on May 24 (= 15:00 UTC, May is CDT
  // which is UTC-5) so we can predict what "today" and "yesterday"
  // mean from the test's perspective.
  const now = new Date('2026-05-24T15:00:00Z');

  it('renders today posts as just the time', () => {
    // 11:36 UTC = 6:36 AM CDT (still May 24 CT)
    const iso = '2026-05-24T11:36:00Z';
    expect(formatPostedAt(iso, now)).toBe('6:36 AM');
  });

  it('renders yesterday posts with the "Yesterday" prefix', () => {
    // 01:00 UTC May 24 = 8:00 PM CDT May 23 (yesterday)
    const iso = '2026-05-24T01:00:00Z';
    expect(formatPostedAt(iso, now)).toBe('Yesterday 8:00 PM');
  });

  it('renders older posts as "Month Day, Time"', () => {
    // 14:00 UTC May 21 = 9:00 AM CDT May 21
    const iso = '2026-05-21T14:00:00Z';
    expect(formatPostedAt(iso, now)).toBe('May 21, 9:00 AM');
  });

  it('treats a naive ISO string (no Z) as UTC, not browser-local', () => {
    // The posts API serializes naive datetimes without a Z suffix.
    // Without the implicit-UTC fix, this string would be parsed as
    // browser-local time and yield a different clock value.
    expect(formatPostedAt('2026-05-24T11:36:00', now)).toBe('6:36 AM');
  });

  it('respects an explicit timezone offset in the input', () => {
    // 12:00 UTC = 7:00 AM CDT
    expect(formatPostedAt('2026-05-24T12:00:00+00:00', now)).toBe('7:00 AM');
  });
});
