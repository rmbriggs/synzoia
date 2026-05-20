import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';

export default function Crews() {
  return (
    <>
      <PageHeader
        title="Your crews"
        description="Private groups where you post your sleep."
      />
      <div className="mt-6 flex gap-3">
        <Button variant="primary" disabled>Create a crew</Button>
        <Button variant="secondary" disabled>Join with code</Button>
      </div>
      <Card className="mt-6">
        <EmptyState message="No crews yet. Coming soon." />
      </Card>
    </>
  );
}
