import { useQuery } from '@tanstack/react-query';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import ErrorCard from '@/components/ui/ErrorCard';
import PageHeader from '@/components/ui/PageHeader';
import FeedSkeleton from '@/components/feed/FeedSkeleton';
import GenericPost from '@/components/feed/GenericPost';
import MilestonePost from '@/components/feed/MilestonePost';
import RecapPost from '@/components/feed/RecapPost';
import SleepPost from '@/components/feed/SleepPost';
import { getFeed } from '@/api/posts';

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
        <ErrorCard
          error={query.error}
          onRetry={() => query.refetch()}
          fallbackMessage="Could not load the feed."
        />
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
            if (post.type === 'sleep') {
              return <SleepPost key={post.id} post={post} />;
            }
            return <GenericPost key={post.id} post={post} />;
          })}
        </div>
      )}
    </div>
  );
}
