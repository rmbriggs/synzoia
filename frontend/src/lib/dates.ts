/**
 * YYYY-MM-DD in the user's local timezone — the "today" they see on
 * their wall clock, not UTC.
 *
 * The backend buckets step rows by `DATE(timestamp)` and the function
 * runs in UTC, so calling `/api/steps/daily` without a date param means
 * the user sees UTC's today. For anyone west of UTC (US, most of the
 * Americas), that's "yesterday" from late afternoon onward — the
 * leaderboard goes empty before midnight local time.
 *
 * Frontends should call backend daily endpoints with `localDate()` as
 * the `?date=` param so each user's "Today" matches their wall clock.
 */
export function localDate(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
