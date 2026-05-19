import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import FormField from '@/components/ui/FormField';
import PageHeader from '@/components/ui/PageHeader';

export default function Settings() {
  return (
    <>
      <PageHeader title="Settings" />
      <Card className="mt-6 space-y-4">
        <h2 className="text-lg font-semibold">Profile</h2>
        <FormField id="settings-display-name" label="Display name" disabled />
        <FormField id="settings-timezone" label="Timezone" disabled />
        <Button variant="primary" disabled>Save</Button>
      </Card>
      <Card className="mt-4">
        <h2 className="text-lg font-semibold">Sign out</h2>
        <p className="text-slate-500 text-sm mt-1">
          Sign out of synzoia on this device.
        </p>
        <Button variant="secondary" className="mt-3" disabled>Sign out</Button>
      </Card>
      <Card className="mt-4">
        <h2 className="text-lg font-semibold">About</h2>
        <p className="text-slate-500 text-sm mt-1">
          synzoia v0.0 — built for UATX Software Engineering Spring 2026.
        </p>
      </Card>
    </>
  );
}
