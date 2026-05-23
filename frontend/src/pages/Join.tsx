import { useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import FormField from '@/components/ui/FormField';
import { ApiError } from '@/api/client';
import { createProfile, type Profile } from '@/api/profiles';

export default function Join() {
  const [username, setUsername] = useState('');
  const [profile, setProfile] = useState<Profile | null>(null);
  const [copied, setCopied] = useState(false);

  const mutation = useMutation({
    mutationFn: createProfile,
    onSuccess: (data) => setProfile(data),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = username.trim();
    if (!trimmed) return;
    mutation.mutate({ username: trimmed });
  }

  async function onCopy() {
    if (!profile) return;
    await navigator.clipboard.writeText(profile.token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (profile) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="max-w-md w-full space-y-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Welcome, {profile.username}.
            </h1>
            <p className="text-muted-foreground text-sm mt-2">
              Here's your token. Paste it into your Siri shortcut so it can
              post your steps. You won't see it again on this device.
            </p>
          </div>
          <div className="bg-muted/40 border border-border rounded-md p-3 font-mono text-sm break-all">
            {profile.token}
          </div>
          <Button variant="primary" className="w-full" onClick={onCopy}>
            {copied ? 'Copied!' : 'Copy token'}
          </Button>
        </Card>
      </div>
    );
  }

  const errMsg = errorMessage(mutation.error);

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="max-w-sm w-full">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">synzoia</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Pick a username. Get a token.
          </p>
        </div>
        <form className="space-y-3 mt-6" onSubmit={onSubmit} noValidate>
          <FormField
            id="username"
            label="Username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g. micah"
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            error={errMsg ?? undefined}
            required
          />
          <Button
            variant="primary"
            className="w-full mt-4"
            type="submit"
            disabled={mutation.isPending || !username.trim()}
          >
            {mutation.isPending ? 'Joining…' : 'Join'}
          </Button>
        </form>
      </Card>
    </div>
  );
}

function errorMessage(err: unknown): string | null {
  if (!err) return null;
  if (err instanceof ApiError) {
    if (err.code === 'username_taken') return 'That username is already taken.';
    if (err.code === 'invalid_username') return err.message;
  }
  return 'Something went wrong. Try again.';
}
