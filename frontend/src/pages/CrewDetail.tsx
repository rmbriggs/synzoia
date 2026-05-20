import { useParams, useSearchParams } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import TabStrip from '@/components/ui/TabStrip';

const TABS = [
  { key: 'feed', label: 'Feed' },
  { key: 'leaderboard', label: 'Leaderboard' },
  { key: 'chat', label: 'Chat' },
];

const TAB_MESSAGES: Record<string, string> = {
  feed: 'Feed coming soon — posts from this crew will appear here.',
  leaderboard: 'Leaderboard coming soon — weekly rankings.',
  chat: 'Chat coming soon — group thread for this crew.',
};

export default function CrewDetail() {
  const { id } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const activeTab = params.get('tab') ?? 'feed';
  const message = TAB_MESSAGES[activeTab] ?? TAB_MESSAGES.feed;

  return (
    <>
      <PageHeader
        title={`Crew ${id}`}
        description="Real crew name lands when backend's ready."
        action={
          <Button variant="primary" to={`/crews/${id}/post`}>
            Post sleep
          </Button>
        }
      />
      <div className="mt-6">
        <TabStrip tabs={TABS} defaultKey="feed" />
      </div>
      <Card className="mt-6">
        <EmptyState message={message} />
      </Card>
    </>
  );
}
