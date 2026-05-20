import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import FormField from '@/components/ui/FormField';
import { devAuth } from '@/lib/auth-dev';

export default function Auth() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>('sign-in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');

  const isSignUp = mode === 'sign-up';
  const devEnabled = devAuth.isEnabled();

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!devEnabled) return;
    if (!email || !password) return;
    if (isSignUp && !displayName) return;
    const effectiveName = isSignUp ? displayName : email.split('@')[0];
    devAuth.signIn(effectiveName, email);
    navigate('/crews');
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="max-w-sm w-full">
        {devEnabled && (
          <div className="text-center mb-3">
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
              Dev mode
            </span>
          </div>
        )}
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">synzoia</h1>
          <p className="text-slate-500 text-sm mt-1">Sleep with friends.</p>
        </div>
        <form className="space-y-3 mt-6" onSubmit={onSubmit}>
          {isSignUp && (
            <FormField
              id="display-name"
              label="Display name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          )}
          <FormField
            id="email"
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <FormField
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button
            variant="primary"
            className="w-full mt-4"
            type="submit"
            disabled={!devEnabled}
          >
            {isSignUp ? 'Sign up' : 'Sign in'}
          </Button>
        </form>
        <p className="text-center text-sm text-slate-500 mt-4">
          {isSignUp ? 'Already have one?' : "Don't have an account?"}{' '}
          <button
            type="button"
            className="text-indigo-600 hover:underline font-medium"
            onClick={() => setMode(isSignUp ? 'sign-in' : 'sign-up')}
          >
            {isSignUp ? 'Sign in' : 'Sign up'}
          </button>
        </p>
      </Card>
    </div>
  );
}
