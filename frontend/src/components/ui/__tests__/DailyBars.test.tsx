import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import DailyBars from '@/components/ui/DailyBars';

function formatDuration(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h}h ${m}m`;
}

describe('DailyBars', () => {
  it('renders a hover tooltip showing each bar\'s formatted value (sleep)', () => {
    render(
      <DailyBars
        days={[
          { date: '2026-06-02', total: 430 },
          { date: '2026-06-01', total: 0 },
        ]}
        cols={7}
        formatValue={formatDuration}
        unit=""
      />,
    );
    // The value is rendered as visible tooltip text, not only a title attr.
    expect(screen.getByText('7h 10m')).toBeInTheDocument(); // 430 min
    expect(screen.getByText('0h 0m')).toBeInTheDocument(); // empty night still hoverable
  });

  it('includes the unit in the tooltip for steps (default formatting)', () => {
    render(<DailyBars days={[{ date: '2026-06-02', total: 12403 }]} />);
    expect(screen.getByText('12,403 steps')).toBeInTheDocument();
  });
});
