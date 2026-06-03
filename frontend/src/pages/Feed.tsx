import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
import { groupPostsByDay } from '@/lib/feedGroups';
import { supabase } from '@/lib/supabase';

export default function Feed() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['posts', 'feed', 50],
    queryFn: () => getFeed(50),
    staleTime: 30_000,
  });

  // Real-time updates (gold "pick one"). Subscribe to INSERTs on
  // `posts` via Supabase Realtime; when a new post lands (sleep
  // session went final, steps milestone, leaderboard recap…), kick
  // the feed query to refetch. We invalidate-then-refetch rather
  // than splicing the realtime payload into the cache because the
  // GET /api/posts response shape (joined username, derived fields,
  // pre-rendered body) is richer than the raw row Realtime ships,
  // and a fresh fetch is cheap (sub-second).
  //
  // Backend prereqs (already in Supabase):
  //   - RLS SELECT policy on `posts` for anon role
  //   - `posts` added to the `supabase_realtime` publication
  //
  // The subscription is per-mount; React StrictMode will double-
  // invoke effects in dev, and removeChannel handles re-mounting
  // cleanly. In prod, one channel per Feed mount.
  useEffect(() => {
    const channel = supabase
      .channel('posts-feed-realtime')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'posts' },
        () => {
          queryClient.invalidateQueries({ queryKey: ['posts'] });
        },
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [queryClient]);

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
        <div className="space-y-8">
          {groupPostsByDay(query.data.posts).map((group) => (
            <section key={group.key} className="space-y-4">
              <div className="flex items-center gap-3">
                <h2 className="label-mono text-muted-foreground">
                  {group.label}
                </h2>
                <div className="h-px flex-1 bg-border/60" />
              </div>
              {group.posts.map((post) => {
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
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
