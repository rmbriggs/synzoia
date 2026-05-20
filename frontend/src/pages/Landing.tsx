import { Link } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import ThemeToggle from '@/components/layout/ThemeToggle';

const features = [
  {
    n: '01',
    title: 'Private crews',
    body: 'Small invite-only groups. No public feed. No algorithm. No strangers. Just the four to twelve people whose mornings actually matter to you.',
  },
  {
    n: '02',
    title: 'The ten-second post',
    body: 'Bedtime. Wake time. An optional line about the night. Less work than typing in the group chat — and your crew sees it the second you post.',
  },
  {
    n: '03',
    title: 'Reactions and the thread',
    body: 'A live feed of your crew’s nights, a tap to react, a thread that finally gets used because everyone is already here every day.',
  },
  {
    n: '04',
    title: 'Streaks and standings',
    body: 'A weekly leaderboard. A longest-streak counter. The kind of friendly competition that turns a habit into a ritual.',
  },
];

const steps = [
  {
    n: '01',
    title: 'Make or join a crew',
    body: 'Start one and pass a code to your group, or drop in with the code a friend just sent you. Crews are invite-only by design.',
  },
  {
    n: '02',
    title: 'Post your sleep',
    body: 'Every morning. Two times and an optional note. Ten seconds, then on with your day.',
  },
  {
    n: '03',
    title: 'Stay in the thread',
    body: 'Watch your crew show up live. React. Talk in the group thread. Climb the board together.',
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top bar */}
      <header className="border-b border-border">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 h-16 flex items-center justify-between">
          <div className="flex items-baseline gap-3">
            <span
              data-logo-slot
              className="font-display italic text-2xl tracking-tight"
            >
              synzoia
            </span>
            <span className="label-mono text-muted-foreground hidden sm:inline">
              est. 2026
            </span>
          </div>
          <div className="flex items-center gap-6">
            <Link
              to="/style-guide"
              className="label-mono text-muted-foreground hover:text-foreground hidden sm:inline transition-colors"
            >
              Style guide
            </Link>
            <Link
              to="/auth"
              className="label-mono text-muted-foreground hover:text-foreground transition-colors"
            >
              Sign in
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main>
        {/* HERO */}
        <section className="relative hero-wash surface-grain overflow-hidden">
          <div className="relative max-w-6xl mx-auto px-6 sm:px-8 pt-24 sm:pt-32 pb-24 sm:pb-40">
            {/* Section marker */}
            <div className="flex items-center gap-3 rise rise-1">
              <span className="hairline w-12" />
              <span className="label-mono text-muted-foreground">
                Issue 01 · Invite-only beta
              </span>
            </div>

            <h1 className="mt-10 font-display text-foreground text-[3.25rem] sm:text-[5.5rem] leading-[0.95] tracking-tight max-w-4xl rise rise-2">
              The daily ritual
              <br />
              that keeps your{' '}
              <em className="text-primary font-display">crew</em> close.
            </h1>

            <p className="mt-8 text-lg sm:text-xl text-muted-foreground max-w-2xl leading-relaxed rise rise-3">
              synzoia is a private group app for crews of four to twelve. You
              post how you slept, you see how your people slept, you talk in the
              thread, you chase streaks together. The group chat your friends
              already wished was a habit.
            </p>

            <div className="mt-12 flex flex-wrap items-center gap-5 rise rise-4">
              <Button variant="primary" to="/auth">
                Get started
              </Button>
              <Link
                to="/auth"
                className="label-mono text-muted-foreground hover:text-foreground border-b border-transparent hover:border-foreground transition-colors pb-0.5"
              >
                I already have an account →
              </Link>
            </div>

            {/* Footer notes inside hero */}
            <div className="mt-20 grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-4 max-w-3xl rise rise-5">
              {[
                ['Crew size', '4 – 12'],
                ['Posts per day', '1'],
                ['Public feed', 'None'],
                ['Algorithm', 'None'],
              ].map(([label, value]) => (
                <div key={label}>
                  <div className="label-mono text-muted-foreground">{label}</div>
                  <div className="font-display italic text-2xl mt-1">{value}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section className="border-t border-border">
          <div className="max-w-6xl mx-auto px-6 sm:px-8 py-24 sm:py-32">
            <div className="grid grid-cols-12 gap-x-6 gap-y-4 mb-16">
              <div className="col-span-12 sm:col-span-3">
                <div className="flex items-center gap-3">
                  <span className="label-mono text-muted-foreground">
                    Section 02
                  </span>
                </div>
              </div>
              <div className="col-span-12 sm:col-span-9">
                <h2 className="font-display text-3xl sm:text-5xl leading-tight tracking-tight">
                  More than{' '}
                  <em className="text-primary">sleep tracking.</em>
                </h2>
                <p className="text-muted-foreground mt-4 max-w-xl">
                  Sleep is the wedge. The product is the part where your
                  group keeps showing up — for each other and for the small,
                  daily things.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-border border border-border">
              {features.map((f) => (
                <article
                  key={f.n}
                  className="bg-background p-8 sm:p-10 group transition-colors hover:bg-accent/30"
                >
                  <div className="flex items-baseline justify-between mb-6">
                    <span className="font-mono text-sm text-muted-foreground">
                      {f.n}
                    </span>
                    <span className="hairline flex-1 ml-4" />
                  </div>
                  <h3 className="font-display text-2xl tracking-tight mb-3">
                    {f.title}
                  </h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {f.body}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* HOW IT WORKS — inverted dark band */}
        <section
          className="border-t border-border"
          style={{
            background: 'var(--foreground)',
            color: 'var(--background)',
          }}
        >
          <div className="max-w-6xl mx-auto px-6 sm:px-8 py-24 sm:py-32">
            <div className="grid grid-cols-12 gap-x-6 gap-y-4 mb-20">
              <div className="col-span-12 sm:col-span-3">
                <span className="label-mono opacity-60">Section 03</span>
              </div>
              <div className="col-span-12 sm:col-span-9">
                <h2 className="font-display text-3xl sm:text-5xl leading-tight tracking-tight">
                  Three steps to a crew that talks{' '}
                  <em>every day.</em>
                </h2>
              </div>
            </div>

            <ol className="space-y-12 sm:space-y-16">
              {steps.map((s) => (
                <li
                  key={s.n}
                  className="grid grid-cols-12 gap-x-6 gap-y-3 items-baseline"
                >
                  <div className="col-span-12 sm:col-span-3">
                    <div className="font-display italic text-5xl sm:text-6xl leading-none">
                      {s.n}
                    </div>
                  </div>
                  <div className="col-span-12 sm:col-span-9 max-w-2xl">
                    <h3 className="font-display text-2xl sm:text-3xl tracking-tight">
                      {s.title}
                    </h3>
                    <p className="opacity-70 mt-3 leading-relaxed">{s.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* PULL QUOTE / FINAL CTA */}
        <section className="border-t border-border hero-wash surface-grain">
          <div className="relative max-w-4xl mx-auto px-6 sm:px-8 py-28 sm:py-36 text-center">
            <span className="label-mono text-muted-foreground">
              Section 04 · Now in beta
            </span>
            <p className="mt-10 font-display italic text-4xl sm:text-6xl leading-[1.05] tracking-tight">
              “The group chat my friends
              <br />
              <span className="text-primary">actually open</span> every day.”
            </p>
            <p className="mt-8 label-mono text-muted-foreground">
              — what synzoia is trying to be
            </p>

            <div className="mt-14 flex items-center justify-center">
              <Button variant="primary" to="/auth">
                Start your crew
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 py-10 grid grid-cols-2 sm:grid-cols-4 gap-6 text-sm">
          <div className="col-span-2">
            <span className="font-display italic text-2xl tracking-tight">
              synzoia
            </span>
            <p className="label-mono text-muted-foreground mt-3">
              Built for crews. Not for strangers.
            </p>
          </div>
          <div>
            <div className="label-mono text-muted-foreground mb-3">Product</div>
            <ul className="space-y-2">
              <li>
                <Link to="/auth" className="hover:text-primary transition-colors">
                  Get started
                </Link>
              </li>
              <li>
                <Link
                  to="/style-guide"
                  className="hover:text-primary transition-colors"
                >
                  Style guide
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <div className="label-mono text-muted-foreground mb-3">Colophon</div>
            <ul className="space-y-2 text-muted-foreground">
              <li>Lora · DM Sans · IBM Plex Mono</li>
              <li>© {new Date().getFullYear()} synzoia</li>
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
}
