import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt, formatDateMedium } from '@/lib/dates';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

export default function RecapPost({ post }: { post: FeedPost }) {
  const top = post.details?.top ?? [];
  const rankedDate = post.details?.date;
  const heading = rankedDate
    ? `Congrats to the top 3 · ${formatDateMedium(rankedDate)}`
    : 'Congrats to the top 3';
  const medals = ['🥇', '🥈', '🥉'];
  const places = ['1st place', '2nd place', '3rd place'];
  return (
    <Card className="bg-accent/10">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h3 className="font-display text-xl tracking-tight">
          <span aria-hidden="true">🏆 </span>
          {heading}
        </h3>
        <span className="label-mono text-muted-foreground">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
      <ol className="space-y-2">
        {top.map((entry, i) => (
          <li
            key={entry.username}
            className="flex items-baseline gap-3"
          >
            <span
              role="img"
              aria-label={places[i] ?? `${i + 1}th place`}
              className="w-6 shrink-0 text-center"
            >
              {medals[i] ?? `#${i + 1}`}
            </span>
            <Link
              to={`/u/${encodeURIComponent(entry.username)}`}
              className="font-medium hover:text-primary transition-colors flex-1 min-w-0 truncate"
            >
              @{entry.username}
            </Link>
            <span className="font-mono tabular-nums">
              {formatNumber(entry.total)}
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}
