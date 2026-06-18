import { Link } from 'react-router-dom';
import { Medal, Trophy } from 'lucide-react';

import UserAvatar from '@/components/ui/UserAvatar';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt, formatDateMedium } from '@/lib/dates';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

// Gold / silver / bronze tints for the top-3 medal icons. Subtle on the
// dark theme -- enough to read as a podium without the loud emoji look.
const MEDAL_TINTS = ['text-amber-300', 'text-slate-300', 'text-amber-600'];
const PLACES = ['1st place', '2nd place', '3rd place'];

export default function RecapPost({ post }: { post: FeedPost }) {
  const top = post.details?.top ?? [];
  const rankedDate = post.details?.date;
  const heading = rankedDate
    ? `Congrats to the top 3 · ${formatDateMedium(rankedDate)}`
    : 'Congrats to the top 3';

  const leader = top[0];
  const metricValue =
    leader ? `@${leader.username} · ${leader.total.toLocaleString()} steps` : null;

  return (
    <div className="surface-glass overflow-hidden mb-0 hover:shadow-md transition-shadow bg-accent/10">
      {/* header */}
      <div className="flex items-baseline justify-between gap-3 px-5 pt-5 pb-3">
        <h3 className="font-display text-xl tracking-tight flex items-center gap-2">
          <Trophy
            size={18}
            strokeWidth={1.75}
            aria-hidden="true"
            className="text-muted-foreground shrink-0"
          />
          {heading}
        </h3>
        <span className="label-mono text-muted-foreground shrink-0">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>

      {/* ranked list */}
      <ol className="space-y-2 px-5 pb-4">
        {top.map((entry, i) => (
          <li key={entry.username} className="flex items-center gap-3">
            <UserAvatar username={entry.username} size="sm" />
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

      {/* footer: metric chip for #1 leader */}
      {metricValue && (
        <div className="px-5 pb-4 flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-primary/10 label-mono text-primary">
            {metricValue}
          </span>
        </div>
      )}
    </div>
  );
}
