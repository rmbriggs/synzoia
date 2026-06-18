import { Link } from 'react-router-dom';

import UserAvatar from '@/components/ui/UserAvatar';
import type { FeedPost, PostType } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';
import { PostTypeIcon, POST_TYPE_META } from '@/components/feed/postType';

function fallbackText(type: PostType): string {
  if (type === 'steps') return 'logged steps';
  if (type === 'workout') return 'logged a workout';
  return 'posted';
}

function typeLabel(type: PostType): string {
  return POST_TYPE_META[type]?.label ?? type;
}

export default function GenericPost({ post }: { post: FeedPost }) {
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
        {post.body ?? fallbackText(post.type)}
      </div>

      {/* footer: type accent pill only (no metric chip for steps/workout) */}
      <div className="px-5 pb-4 flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent/60 label-mono text-accent-foreground">
          <PostTypeIcon type={post.type} />
          {typeLabel(post.type)}
        </span>
      </div>
    </div>
  );
}
