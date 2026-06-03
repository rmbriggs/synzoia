import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import FormField from '@/components/ui/FormField';
import { supabase } from '@/lib/supabase';

/**
 * Sign-in page (added in C2). Pairs with /join for signup.
 *
 * Why a separate page from /join: the signup form has more state
 * (email + password + username + the "here's your token" success
 * screen), and conflating them with login made both flows worse.
 * Keeping login a one-purpose page keeps it phone-friendly and
 * keyboard-accessible.
 *
 * After a successful sign-in, the Supabase session lands in
 * localStorage automatically (via supabase-js's default persistence)
 * and useAuthSession's onAuthStateChange listener picks it up.
 * Routing the user away from /login means they don't see the form
 * a second time on refresh.
 */
export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) return;
    setPending(true);
    setError(null);
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: trimmedEmail,
      password,
    });
    if (signInError) {
      setError(translateAuthError(signInError.message));
      setPending(false);
      return;
    }
    // Successful sign-in — Supabase has persisted the session.
    // Send the user to the feed; useAuthSession picks up the new
    // state through onAuthStateChange.
    navigate('/feed');
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="max-w-sm w-full">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">synzoia</h1>
          <p className="text-muted-foreground text-sm mt-1">Welcome back.</p>
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
            placeholder="••••••••"
            autoComplete="current-password"
            error={error ?? undefined}
            required
          />
          <Button
            variant="primary"
            className="w-full mt-4"
            type="submit"
            disabled={pending || !email.trim() || !password}
          >
            {pending ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
        <p className="text-center text-sm text-muted-foreground mt-4">
          New here?{' '}
          <a
            href="/join"
            className="text-primary hover:underline"
          >
            Create an account
          </a>
        </p>
      </Card>
    </div>
  );
}

/**
 * Supabase Auth returns generic error strings ("Invalid login
 * credentials", "User not found"). Map to user-friendly text and
 * deliberately collapse "no such user" + "bad password" to a
 * single message — that prevents the UI from being used as an
 * oracle to enumerate which emails have accounts.
 */
function translateAuthError(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes('invalid') || lower.includes('credentials')) {
    return 'Email or password is incorrect.';
  }
  if (lower.includes('email not confirmed')) {
    return 'Check your email and confirm your address before signing in.';
  }
  return 'Sign in failed. Please try again.';
}
