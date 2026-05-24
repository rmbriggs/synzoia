/**
 * Centralized timezone handling for synzoia.
 *
 * synzoia displays everything in Central Time regardless of where the
 * viewer is — the audience is Central-based and the iOS Shortcut that
 * writes step timestamps lives on Central-time iPhones, so anchoring
 * the website to the same zone keeps "today" and "this week" consistent
 * with the data being posted.
 *
 * The database itself stays in UTC (timestamptz columns) and naive
 * local-time (steps.timestamp, posts.timestamp). This module only
 * affects what the browser shows and what date the frontend treats as
 * "today" when calling the API.
 */

export const APP_TIMEZONE = 'America/Chicago';

const ISO_DATE_PARTS = new Intl.DateTimeFormat('en-CA', {
  timeZone: APP_TIMEZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

/**
 * Today's date in the app timezone as YYYY-MM-DD. Use this whenever
 * the frontend needs to pass `?date=` to an endpoint that buckets by
 * date — the user's wall clock in CT is the canonical "today".
 */
export function currentDate(): string {
  // en-CA's date format is already YYYY-MM-DD, which is exactly what
  // the API expects.
  return ISO_DATE_PARTS.format(new Date());
}

/**
 * Backwards-compat alias. The previous helper returned the *browser's*
 * local date — which was usually CT for the people who use this app,
 * but not always. Keeping the name so existing call sites don't need
 * touching all at once; the behavior is now CT-anchored everywhere.
 */
export const localDate = currentDate;

/**
 * Format a bare YYYY-MM-DD date string for display ("Saturday, May 23").
 * No timezone math — bare dates are calendar concepts, not points in
 * time. Reads from the string directly to avoid the "new Date(iso)"
 * trap that re-interprets a date as midnight UTC.
 */
export function formatDateLong(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
}

/**
 * Like formatDateLong but without the weekday — "May 23, 2026".
 */
export function formatDateMedium(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Format a UTC ISO timestamp ("2026-05-24T01:52:35.866153Z") for
 * display in app timezone — "May 23, 2026". Use for timestamptz
 * fields like profiles.join_date that arrive as zoned UTC strings.
 */
export function formatTimestampDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    timeZone: APP_TIMEZONE,
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}
