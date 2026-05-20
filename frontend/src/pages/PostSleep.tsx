import { useParams } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import FormField from '@/components/ui/FormField';
import PageHeader from '@/components/ui/PageHeader';

export default function PostSleep() {
  const { id } = useParams<{ id: string }>();
  return (
    <>
      <PageHeader
        title="Post your sleep"
        description="How'd you sleep last night?"
      />
      <Card className="mt-6 space-y-4">
        <FormField id="bedtime" label="Bedtime" type="datetime-local" disabled />
        <FormField id="wake" label="Wake time" type="datetime-local" disabled />
        <FormField
          id="quality"
          label="Quality (1–100)"
          type="number"
          min={1}
          max={100}
          disabled
        />
        <FormField
          id="note"
          label="Note (optional, up to 280 chars)"
          type="text"
          disabled
        />
        <div className="flex gap-3 pt-2">
          <Button variant="primary" disabled>Post</Button>
          <Button variant="ghost" to={`/crews/${id}`}>Cancel</Button>
        </div>
      </Card>
    </>
  );
}
