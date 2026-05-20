import { useParams, useSearchParams } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import TabStrip from '@/components/ui/TabStrip';
import SleepPost from '@/components/feed/SleepPost';
import LeaderboardRow from '@/components/feed/LeaderboardRow';
import ChatMessage from '@/components/feed/ChatMessage';
import {
  getCrew,
  getLeaderboardForCrew,
  listMessagesForCrew,
  listPostsForCrew,
} from '@/lib/mockData';

const TABS = [
  { key: 'feed', label: 'Feed' },
  { key: 'leaderboard', label: 'Leaderboard' },
  { key: 'chat', label: 'Chat' },
];

export default function CrewDetail() {
  const { id } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const activeTab = params.get('tab') ?? 'feed';

  const crew = id ? getCrew(id) : undefined;

  if (!crew) {
    return (
      <>
        <PageHeader
          title="Crew not found"
          description="This crew doesn't exist in the mock data layer."
        />
        <Card className="mt-6">
          <EmptyState message="Try /crews/c-owls or /crews/c-capstone." />
        </Card>
      </>
    );
  }

  const posts = listPostsForCrew(crew.id);
  const leaderboard = getLeaderboardForCrew(crew.id);
  const messages = listMessagesForCrew(crew.id);

  return (
    <>
      <PageHeader
        title={crew.name}
        description={`${crew.memberIds.length} members`}
        action={
          <Button variant="primary" to={`/crews/${crew.id}/post`}>
            Post sleep
          </Button>
        }
      />
      <div className="mt-6">
        <TabStrip tabs={TABS} defaultKey="feed" />
      </div>

      {activeTab === 'feed' && (
        <Card className="mt-6">
          {posts.length === 0 ? (
            <EmptyState message="No posts yet — your crew is still asleep." />
          ) : (
            <div>
              {posts.map((p) => (
                <SleepPost key={p.id} post={p} />
              ))}
            </div>
          )}
        </Card>
      )}

      {activeTab === 'leaderboard' && (
        <Card className="mt-6">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="font-display text-xl tracking-tight">This week</h2>
            <span className="label-mono text-muted-foreground">
              Resets Sunday
            </span>
          </div>
          {leaderboard.length === 0 ? (
            <EmptyState />
          ) : (
            <ol>
              {leaderboard.map((entry) => (
                <LeaderboardRow key={entry.userId} entry={entry} />
              ))}
            </ol>
          )}
        </Card>
      )}

      {activeTab === 'chat' && (
        <Card className="mt-6">
          {messages.length === 0 ? (
            <EmptyState message="No messages yet. Start the thread." />
          ) : (
            <div className="space-y-5">
              {messages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}
            </div>
          )}
        </Card>
      )}
    </>
  );
}
