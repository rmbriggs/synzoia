import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import { ApiError } from '@/api/client';
import { getFeed, type FeedPost } from '@/api/posts';
import { formatPostedAt } from '@/lib/dates';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function MilestonePost({ post }: { post: FeedPost }) {
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
          {post.body ?? 'hit a milestone'}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}

function RecapPost({ post }: { post: FeedPost }) {
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

function GenericPost({ post }: { post: FeedPost }) {
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
          {post.body ?? `posted (${post.type})`}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatPostedAt(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}

function FeedSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <div className="flex items-baseline gap-3">
            <span className="h-3 w-20 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 flex-1 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 w-12 bg-muted/60 rounded animate-pulse" />
          </div>
        </Card>
      ))}
    </div>
  );
}

function ErrorCard({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : 'Could not load the feed.';
  return (
    <Card className="border-destructive/40 bg-destructive/5">
      <p className="text-destructive text-sm">{message}</p>
      <Button variant="secondary" className="mt-3" onClick={onRetry}>
        Try again
      </Button>
    </Card>
  );
}

export default function Feed() {
  const query = useQuery({
    queryKey: ['posts', 'feed', 50],
    queryFn: () => getFeed(50),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Feed"
        description="Recent milestones and recaps."
      />

      {query.isPending ? (
        <FeedSkeleton />
      ) : query.isError ? (
        <ErrorCard error={query.error} onRetry={() => query.refetch()} />
      ) : query.data.posts.length === 0 ? (
        <Card>
          <EmptyState message="No posts yet. Start walking." />
        </Card>
      ) : (
        <div className="space-y-4">
          {query.data.posts.map((post) => {
            if (post.type === 'leaderboard_recap') {
              return <RecapPost key={post.id} post={post} />;
            }
            if (post.type === 'steps_milestone') {
              return <MilestonePost key={post.id} post={post} />;
            }
            return <GenericPost key={post.id} post={post} />;
          })}
        </div>
      )}
    </div>
  );
}
