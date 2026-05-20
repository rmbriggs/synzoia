import Button from '@/components/ui/AppButton';
import PageHeader from '@/components/ui/PageHeader';
import CrewListItem from '@/components/feed/CrewListItem';
import { currentUserId, listCrewsForUser } from '@/lib/mockData';

export default function Crews() {
  const myCrews = listCrewsForUser(currentUserId);

  return (
    <>
      <PageHeader
        title="Your crews"
        description="Private groups where you post your sleep."
      />
      <div className="mt-6 flex gap-3">
        <Button variant="primary" disabled>
          Create a crew
        </Button>
        <Button variant="secondary" disabled>
          Join with code
        </Button>
      </div>

      <div className="mt-8 space-y-4">
        {myCrews.map((crew) => (
          <CrewListItem key={crew.id} crew={crew} />
        ))}
      </div>
    </>
  );
}
