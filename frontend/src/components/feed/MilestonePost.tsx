import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';
import { PostTypeIcon } from '@/components/feed/postType';

export default function MilestonePost({ post }: { post: FeedPost }) {
  return (
    <Card>
      <div className="flex items-center gap-3">
        <PostTypeIcon type={post.type} />
        <Link
          to={`/u/${encodeURIComponent(post.username)}`}
          className="font-medium hover:text-primary transition-colors"
        >
          @{post.username}
        </Link>
        <span className="text-muted-foreground">
          {post.body ?? 'hit a milestone'}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}
