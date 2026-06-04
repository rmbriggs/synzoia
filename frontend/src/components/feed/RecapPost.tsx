import { Link } from 'react-router-dom';
import { Medal, Trophy } from 'lucide-react';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt, formatDateMedium } from '@/lib/dates';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

// Gold / silver / bronze tints for the top-3 medal icons. Subtle on the
// dark theme — enough to read as a podium without the loud emoji look.
const MEDAL_TINTS = ['text-amber-300', 'text-slate-300', 'text-amber-600'];
const PLACES = ['1st place', '2nd place', '3rd place'];

export default function RecapPost({ post }: { post: FeedPost }) {
  const top = post.details?.top ?? [];
  const rankedDate = post.details?.date;
  const heading = rankedDate
    ? `Congrats to the top 3 · ${formatDateMedium(rankedDate)}`
    : 'Congrats to the top 3';
  return (
    <Card className="bg-accent/10">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h3 className="font-display text-xl tracking-tight flex items-center gap-2">
          <Trophy
            size={18}
            strokeWidth={1.75}
            aria-hidden="true"
            className="text-muted-foreground shrink-0"
          />
          {heading}
        </h3>
        <span className="label-mono text-muted-foreground">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
      <ol className="space-y-2">
        {top.map((entry, i) => (
          <li key={entry.username} className="flex items-center gap-3">
            {i < 3 ? (
              <Medal
                size={18}
                strokeWidth={1.75}
                role="img"
                aria-label={PLACES[i]}
                className={`shrink-0 ${MEDAL_TINTS[i]}`}
              />
            ) : (
              <span
                role="img"
                aria-label={`${i + 1}th place`}
                className="w-[18px] shrink-0 text-center label-mono text-muted-foreground"
              >
                #{i + 1}
              </span>
            )}
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
