import { useState } from 'react';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import FormField from '@/components/ui/FormField';

export default function Auth() {
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>('sign-in');
  const isSignUp = mode === 'sign-up';

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="max-w-sm w-full">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">synzoia</h1>
          <p className="text-slate-500 text-sm mt-1">Sleep with friends.</p>
        </div>
        <div className="space-y-3 mt-6">
          {isSignUp && (
            <FormField id="display-name" label="Display name" type="text" />
          )}
          <FormField id="email" label="Email" type="email" />
          <FormField id="password" label="Password" type="password" />
        </div>
        <Button variant="primary" className="w-full mt-4" disabled>
          {isSignUp ? 'Sign up' : 'Sign in'}
        </Button>
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
