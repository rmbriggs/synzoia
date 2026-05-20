import { useNavigate } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import FormField from '@/components/ui/FormField';
import PageHeader from '@/components/ui/PageHeader';
import { useAuthSession } from '@/hooks/useAuthSession';
import { devAuth } from '@/lib/auth-dev';

export default function Settings() {
  const navigate = useNavigate();
  const { session } = useAuthSession();
  const devEnabled = devAuth.isEnabled();
  const canSignOut = devEnabled && session !== null;

  function onSignOut() {
    devAuth.signOut();
    navigate('/auth');
  }

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
        <Button
          variant="secondary"
          className="mt-3"
          disabled={!canSignOut}
          onClick={onSignOut}
        >
          Sign out
        </Button>
      </Card>
      <Card className="mt-4">
        <h2 className="text-lg font-semibold">About</h2>
        <p className="text-slate-500 text-sm mt-1">
          synzoia v0.0 — built for UATX Software Engineering Spring 2026.
        </p>
        {devEnabled && (
          <p className="text-xs text-amber-700 mt-2">
            Running in dev-fake-auth mode.
          </p>
        )}
      </Card>
    </>
  );
}
