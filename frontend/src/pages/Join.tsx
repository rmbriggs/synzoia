import { useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';

import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import FormField from '@/components/ui/FormField';
import { ApiError } from '@/api/client';
import { createProfile, type Profile } from '@/api/profiles';
import { supabase } from '@/lib/supabase';

/**
 * Signup page, post-C2.
 *
 * Three-step flow under the hood, single click for the user:
 *
 *   1. supabase.auth.signUp(email, password, { data: { username } })
 *      — creates the row in Supabase's `auth.users` and gives us a
 *      session (JWT).
 *   2. POST /api/profiles { username } with that JWT — creates the
 *      linked row in OUR `profiles` table and returns a long-lived
 *      opaque token for the iOS Shortcut.
 *   3. Show the token to the user once (it's the only time we have
 *      the plaintext on the client; future visits show "..." in its
 *      place).
 *
 * Optimistic UI (silver invariant):
 *   The success screen flips on immediately when the user clicks
 *   "Join", BEFORE step 1 has returned. If signup fails (e.g.,
 *   "email already registered" or network blip), we roll back to
 *   the form and surface the error. This is "optimistic updates
 *   with rollback on failure" per the final-project spec page 8.
 */
export default function Join() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');

  // `profile` holds the eventual server response so we can show the
  // token in the success view. `optimistic` is the silver-invariant
  // optimistic-UI piece: we set the success view BEFORE the network
  // request completes, then either keep it (success → fill in token)
  // or roll back (failure → show form again with error).
  const [profile, setProfile] = useState<Profile | null>(null);
  const [optimistic, setOptimistic] = useState(false);
  const [copied, setCopied] = useState(false);

  const mutation = useMutation({
    mutationFn: async (vars: {
      email: string;
      password: string;
      username: string;
    }) => {
      // Step 1: create the Supabase Auth user. The `data: { username }`
      // option tucks the chosen username into user_metadata, which
      // useAuthSession reads for header chrome (avoids a separate
      // round-trip to /api/profiles just to render "@max").
      const { data, error } = await supabase.auth.signUp({
        email: vars.email,
        password: vars.password,
        options: { data: { username: vars.username } },
      });
      if (error) throw error;
      if (!data.session) {
        // Supabase can be configured to require email confirmation
        // before issuing a session. If we get here, the row was
        // created but the user can't yet act as themselves —
        // surface this as a known-state error rather than crashing.
        throw new Error('check-email');
      }
      // Step 2: create the linked profile + machine token. apiFetch
      // reads the just-installed Supabase session and attaches the
      // JWT automatically.
      return createProfile({ username: vars.username });
    },
    onMutate: () => {
      // OPTIMISTIC: flip to the success view immediately. If the
      // mutation rejects, onError below flips it back.
      setOptimistic(true);
    },
    onSuccess: (created) => {
      // Server confirmed — replace the optimistic state with the
      // real Profile object so we can show the token.
      setProfile(created);
    },
    onError: () => {
      // ROLLBACK: drop back to the form with the error visible.
      setOptimistic(false);
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmedEmail = email.trim();
    const trimmedUsername = username.trim();
    if (!trimmedEmail || !password || !trimmedUsername) return;
    mutation.mutate({
      email: trimmedEmail,
      password,
      username: trimmedUsername,
    });
  }

  async function onCopy() {
    if (!profile) return;
    await navigator.clipboard.writeText(profile.token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // Success view — shown OPTIMISTICALLY (no token yet) and then
  // again once the server confirms (with the token). The two states
  // look almost identical so the user perceives the signup as
  // instant; the only delta is the token block flipping from a
  // shimmering placeholder to the real string.
  if (optimistic || profile) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="max-w-md w-full space-y-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {profile
                ? `Welcome, ${profile.username}.`
                : `Welcome, ${username || 'friend'}.`}
            </h1>
            <p className="text-muted-foreground text-sm mt-2">
              Here's your token. Paste it into your Siri shortcut so it can
              post your steps. You won't see it again on this device.
            </p>
          </div>
          {profile ? (
            <div className="bg-muted/40 border border-border rounded-md p-3 font-mono text-sm break-all">
              {profile.token}
            </div>
          ) : (
            // Optimistic placeholder while the network request is
            // in flight. Same dimensions as the real token block so
            // the layout doesn't jump when the value lands.
            <div
              className="bg-muted/40 border border-border rounded-md p-3 font-mono text-sm h-12 animate-pulse"
              aria-label="Generating your token"
            />
          )}
          <Button
            variant="primary"
            className="w-full"
            onClick={onCopy}
            disabled={!profile}
          >
            {copied ? 'Copied!' : profile ? 'Copy token' : 'Almost there…'}
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
            Sign up. Get a token. Start logging.
          </p>
        </div>
        <form className="space-y-3 mt-6" onSubmit={onSubmit} noValidate>
          <FormField
            id="email"
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            autoCapitalize="none"
            spellCheck={false}
            required
          />
          <FormField
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 6 characters"
            autoComplete="new-password"
            required
          />
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
            disabled={
              mutation.isPending ||
              !email.trim() ||
              !password ||
              !username.trim()
            }
          >
            {mutation.isPending ? 'Joining…' : 'Join'}
          </Button>
        </form>
        <p className="text-center text-sm text-muted-foreground mt-4">
          Already have an account?{' '}
          <a href="/login" className="text-primary hover:underline">
            Sign in
          </a>
        </p>
      </Card>
    </div>
  );
}

function errorMessage(err: unknown): string | null {
  if (!err) return null;
  if (err instanceof ApiError) {
    if (err.code === 'username_taken') return 'That username is already taken.';
    if (err.code === 'invalid_username') return err.message;
    if (err.code === 'unauthenticated')
      return "Signup didn't complete. Try again.";
  }
  // Supabase Auth errors are objects with a `message` string but
  // (depending on the version) may not extend Error. Duck-type on
  // the message field so both real and mocked errors match.
  const raw =
    typeof (err as { message?: unknown })?.message === 'string'
      ? ((err as { message: string }).message)
      : '';
  const msg = raw.toLowerCase();
  if (raw === 'check-email') {
    return 'Check your email to confirm your address, then sign in.';
  }
  if (msg.includes('already registered') || msg.includes('already exists')) {
    return 'That email already has an account. Try signing in instead.';
  }
  if (msg.includes('password')) {
    return 'Password must be at least 6 characters.';
  }
  return 'Something went wrong. Try again.';
}
