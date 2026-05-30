import type { DailyTotal } from '@/api/steps';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

interface DailyBarsProps {
  days: DailyTotal[];
  /** Number of grid columns; defaults to days.length. Use 7 for a week,
   *  28-31 for a month. */
  cols?: number;
  /** Formats a day's value for the tooltip/aria-label. Defaults to a
   *  plain number (steps). Sleep passes formatDuration. */
  formatValue?: (n: number) => string;
  /** Unit suffix appended to the aria-label, e.g. "steps". Pass "" to
   *  omit (sleep's formatValue already reads as "7h 32m"). */
  unit?: string;
}

export default function DailyBars({
  days,
  cols,
  formatValue = formatNumber,
  unit = 'steps',
}: DailyBarsProps) {
  const n = cols ?? days.length;
  const max = Math.max(...days.map((d) => d.total), 1);
  return (
    <div
      className="grid gap-2 h-28 items-end"
      style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}
    >
      {days.map((d) => {
        const heightPct = (d.total / max) * 100;
        const valueLabel = unit
          ? `${formatValue(d.total)} ${unit}`
          : formatValue(d.total);
        return (
          <div
            key={d.date}
            className="flex flex-col items-center gap-1.5 h-full"
            title={`${d.date}: ${formatValue(d.total)}`}
          >
            <div className="flex-1 w-full flex items-end">
              <div
                className="w-full bg-primary/70 rounded-t"
                style={{ height: `${Math.max(heightPct, 2)}%` }}
                aria-label={`${d.date}: ${valueLabel}`}
              />
            </div>
            <span className="label-mono text-[10px] text-muted-foreground">
              {d.date.slice(-2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
