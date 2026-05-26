import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

export default function RecapPost({ post }: { post: FeedPost }) {
  const top = post.details?.top ?? [];
  return (
    <Card className="bg-accent/10">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h3 className="font-display text-xl tracking-tight">
          Yesterday&rsquo;s top 3
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
            <span className="label-mono w-6 shrink-0 text-muted-foreground">
              #{i + 1}
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
