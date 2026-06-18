// Consecutive days ending at `today` (YYYY-MM-DD) with a recorded total > 0.
// `days` need not be sorted. Walks backwards one calendar day at a time.
export function currentStreak(
  days: { date: string; total: number }[],
  today: string,
): number {
  const byDate = new Map(days.map((d) => [d.date, d.total]));
  let streak = 0;
  const cursor = new Date(`${today}T00:00:00Z`);
  for (;;) {
    const key = cursor.toISOString().slice(0, 10);
    const total = byDate.get(key);
    if (total === undefined || total <= 0) break;
    streak += 1;
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return streak;
}
