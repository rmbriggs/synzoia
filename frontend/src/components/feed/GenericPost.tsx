import { Link } from 'react-router-dom';

import Card from '@/components/ui/AppCard';
import type { FeedPost, PostType } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';
import { PostTypeIcon } from '@/components/feed/postType';

function fallbackText(type: PostType): string {
  if (type === 'steps') return 'logged steps';
  if (type === 'workout') return 'logged a workout';
  return 'posted';
}

export default function GenericPost({ post }: { post: FeedPost }) {
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
          {post.body ?? fallbackText(post.type)}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}
