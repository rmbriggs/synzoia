/**
 * Average value over only the days that actually have data.
 *
 * The week/month cards show this instead of a window total: for sleep a
 * total ("21h41m this week") is meaningless, and dividing by every day in
 * the window would count un-logged days as 0 and drag the number down.
 * Averaging over logged days answers "how much on a typical day".
 *
 * Returns a rounded integer (minutes for sleep, steps for steps); 0 when
 * no day in the range has data.
 */
export function averagePerLoggedDay(days: { total: number }[]): number {
  const logged = days.filter((d) => d.total > 0);
  if (logged.length === 0) return 0;
  const sum = logged.reduce((acc, d) => acc + d.total, 0);
  return Math.round(sum / logged.length);
}
