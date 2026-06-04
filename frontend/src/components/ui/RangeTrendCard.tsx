import { useState } from 'react';

import Card from '@/components/ui/AppCard';
import DailyBars from '@/components/ui/DailyBars';
import ErrorCard from '@/components/ui/ErrorCard';
import { averagePerLoggedDay } from '@/lib/stats';
import type { DailyTotal } from '@/api/steps';

type Range = '7d' | '30d';

/**
 * One range's worth of chart state, flattened from a React Query result at
 * the call site so this component doesn't depend on the steps-vs-sleep
 * response shapes. `days` / `total` / `rank` are only read once the slice is
 * ready (not pending, not errored).
 */
export interface RangeSlice {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  days: DailyTotal[];
  total: number;
  rank: number | null;
}

interface RangeTrendCardProps {
  week: RangeSlice;
  month: RangeSlice;
  /** Formats a value for the avg readout + bar tooltips. Defaults to a plain
   *  number (steps). Sleep passes formatDuration. */
  formatValue?: (n: number) => string;
  /** Unit suffix for the avg readout + bar labels. '' for sleep. */
  unit?: string;
  /** Shown under the 30-day view when there's no activity in the window. */
  emptyMonthMessage: string;
}

function RangeToggle({
  range,
  onChange,
}: {
  range: Range;
  onChange: (r: Range) => void;
}) {
  const options: ReadonlyArray<readonly [Range, string]> = [
    ['7d', '7D'],
    ['30d', '30D'],
  ];
  return (
    <div
      role="tablist"
      aria-label="Chart range"
      className="inline-flex rounded-lg border border-border/60 bg-muted/30 p-0.5"
    >
      {options.map(([key, label]) => (
        <button
          key={key}
          type="button"
          role="tab"
          aria-selected={range === key}
          onClick={() => onChange(key)}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            range === key
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/**
 * A single card that merges the "Last 7 days" and "Last 30 days" charts
 * behind a 7D/30D toggle, with a zoom transition between ranges (see the
 * .zoom-in / .zoom-out keyframes in index.css). Both ranges' queries run
 * up front, so toggling is instant.
 */
export default function RangeTrendCard({
  week,
  month,
  formatValue = (n) => n.toLocaleString(),
  unit = 'steps',
  emptyMonthMessage,
}: RangeTrendCardProps) {
  const [range, setRange] = useState<Range>('7d');
  const active = range === '7d' ? week : month;

  const ready = !active.isPending && !active.isError;
  const meta = ready ? (
    <>
      {active.total > 0
        ? `avg ${formatValue(averagePerLoggedDay(active.days))}${unit ? ` ${unit}` : ''}`
        : '—'}
      {' · '}
      {active.rank !== null ? `#${active.rank}` : '—'}
    </>
  ) : null;

  return (
    <Card>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <RangeToggle range={range} onChange={setRange} />
        <span className="label-mono text-muted-foreground">{meta}</span>
      </div>

      {/* key={range} remounts the body on each toggle so the zoom animation
          replays; the direction depends on which range we're entering. */}
      <div key={range} className={range === '30d' ? 'zoom-out' : 'zoom-in'}>
        {active.isPending ? (
          <div className="h-28 animate-pulse rounded bg-muted/40" />
        ) : active.isError ? (
          <ErrorCard
            error={active.error}
            onRetry={active.onRetry}
            fallbackMessage="Could not load this chart."
          />
        ) : range === '30d' && active.days.length === 0 ? (
          <div className="label-mono italic text-muted-foreground">
            {emptyMonthMessage}
          </div>
        ) : (
          <DailyBars
            days={active.days}
            cols={range === '7d' ? 7 : undefined}
            formatValue={formatValue}
            unit={unit}
          />
        )}
      </div>
    </Card>
  );
}
