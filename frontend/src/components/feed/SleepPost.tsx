import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';

export default function SleepPost({ post }: { post: FeedPost }) {
  return (
    <Card>
      <div className="flex items-baseline gap-3">
        <Link
          to={`/u/${encodeURIComponent(post.username)}`}
          className="font-medium hover:text-primary transition-colors"
        >
          @{post.username}
        </Link>
        <span className="text-muted-foreground">
          <span aria-hidden="true">🌙 </span>
          <span>{post.body ?? 'logged sleep'}</span>
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}
