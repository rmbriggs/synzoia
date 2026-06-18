import { Link } from 'react-router-dom';
import { Trophy } from 'lucide-react';

import UserAvatar from '@/components/ui/UserAvatar';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';

export default function MilestonePost({ post }: { post: FeedPost }) {
  const threshold = post.details?.threshold;
  const metricValue =
    threshold != null ? `${threshold.toLocaleString()} step milestone` : null;

  return (
    <div className="surface-glass overflow-hidden mb-0 hover:shadow-md transition-shadow">
      {/* header */}
      <div className="flex items-center gap-3 px-5 pt-5 pb-3">
        <UserAvatar username={post.username} size="sm" />
        <div className="flex-1 min-w-0">
          <Link
            to={`/u/${encodeURIComponent(post.username)}`}
            className="font-semibold text-sm hover:text-primary transition-colors"
          >
            @{post.username}
          </Link>
        </div>
        <span className="label-mono text-muted-foreground shrink-0">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>

      {/* body */}
      <div className="px-5 pb-4 text-sm text-muted-foreground leading-relaxed">
        {post.body ?? 'hit a milestone'}
      </div>

      {/* footer: trophy accent + optional milestone chip */}
      <div className="px-5 pb-4 flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent/60 label-mono text-accent-foreground">
          <Trophy
            size={14}
            strokeWidth={1.75}
            aria-hidden="true"
            className="shrink-0"
          />
          Milestone
        </span>
        {metricValue && (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-primary/10 label-mono text-primary">
            {metricValue}
          </span>
        )}
      </div>
    </div>
  );
}
