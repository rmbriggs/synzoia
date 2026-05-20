import { Link } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';

const features = [
  {
    title: 'Private crews',
    body: 'Small groups of close friends. No public feed, no algorithm, no strangers. Just your people.',
  },
  {
    title: 'The 10-second post',
    body: 'Bedtime, wake time, one optional note. Drop your night, see everyone else’s.',
  },
  {
    title: 'React and chat',
    body: 'Live reactions on every post. A group thread that’s actually used because everyone’s here every day.',
  },
  {
    title: 'Streaks and standings',
    body: 'Friendly weekly leaderboards. Longest-streak counters. Lightweight competition that keeps the ritual going.',
  },
];

const steps = [
  {
    title: 'Make or join a crew',
    body: 'Crews are invite-only. Start one and send a code to your group, or drop in with the code your friend just sent you.',
  },
  {
    title: 'Post your sleep',
    body: 'Every morning. Bedtime, wake time, optional note. It takes ten seconds.',
  },
  {
    title: 'Stay in the thread',
    body: 'Watch your crew’s nights show up live, react, talk in the thread, climb the board together.',
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <span
            data-logo-slot
            className="text-lg font-semibold tracking-tight text-foreground"
          >
            synzoia
          </span>
          <Link
            to="/auth"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Sign in
          </Link>
        </div>
      </header>

      <main>
        <section className="px-4 sm:px-6 pt-20 pb-24 sm:pt-28 sm:pb-32">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-foreground">
              The daily ritual that keeps your crew close.
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Private groups where your people post their sleep, react to each
              other&rsquo;s nights, talk in the thread, and chase streaks
              together. Real-time. Invite-only. Built for crews of 4&ndash;12.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <Button variant="primary" to="/auth">
                Get started
              </Button>
              <Link
                to="/auth"
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                I already have an account
              </Link>
            </div>
          </div>
        </section>

        <section className="border-t border-border bg-muted/30">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-20 space-y-10">
            <div className="max-w-2xl">
              <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight">
                More than sleep tracking.
              </h2>
              <p className="text-muted-foreground mt-2">
                Sleep is the wedge. Connection is the product.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {features.map((f) => (
                <Card key={f.title}>
                  <h3 className="text-lg font-semibold">{f.title}</h3>
                  <p className="text-muted-foreground text-sm mt-2 leading-relaxed">
                    {f.body}
                  </p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="border-t border-border">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-20 space-y-10">
            <div className="max-w-2xl">
              <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight">
                How it works
              </h2>
              <p className="text-muted-foreground mt-2">
                Three steps to a crew that talks every day.
              </p>
            </div>
            <ol className="space-y-6">
              {steps.map((s, i) => (
                <li key={s.title} className="flex gap-4 sm:gap-6">
                  <span className="shrink-0 w-9 h-9 rounded-full bg-primary text-primary-foreground font-semibold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <div>
                    <h3 className="text-lg font-semibold">{s.title}</h3>
                    <p className="text-muted-foreground text-sm mt-1 leading-relaxed">
                      {s.body}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="border-t border-border bg-muted/30">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-20 sm:py-24 text-center space-y-5">
            <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight">
              Ready to start your crew?
            </h2>
            <p className="text-muted-foreground">
              Sign up takes a minute. Your group will have a thread by tomorrow
              morning.
            </p>
            <div className="pt-2">
              <Button variant="primary" to="/auth">
                Get started
              </Button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-muted-foreground">
          <span>&copy; {new Date().getFullYear()} synzoia</span>
          <span>Built for crews. Not for strangers.</span>
        </div>
      </footer>
    </div>
  );
}
