import { Link } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import ThemeToggle from '@/components/layout/ThemeToggle';
import WaveCurve from '@/components/ui/WaveCurve';

const features = [
  {
    n: '01',
    title: 'Public by default',
    body: 'No followers. No friend graph. Every count is visible to every user. The whole point is that someone you have never met is walking right now too.',
  },
  {
    n: '02',
    title: 'Apple Health, automatically',
    body: 'A Siri Shortcut pulls your step count from Apple Health and posts it for you. Set it up once. After that, nothing — your phone does the daily check-in.',
  },
  {
    n: '03',
    title: 'Daily, weekly, all-time',
    body: 'Three leaderboards. Today’s leader. The week’s grind. The all-time best. The kind of friendly competition you can show a friend on a screenshot.',
  },
  {
    n: '04',
    title: 'A profile per walker',
    body: 'Total steps. Best day. Current rank. Days active. The minimum viable record of who has been showing up, and how much.',
  },
];

const steps = [
  {
    n: '01',
    title: 'Pick a username',
    body: 'Type one in. We give you back a token — four blocks of four uppercase letters. Don’t lose it; we don’t store a way to recover it.',
  },
  {
    n: '02',
    title: 'Install the Shortcut',
    body: 'One-tap install on iPhone. Paste your token in. The Shortcut reads your Apple Health step count and POSTs it on your behalf.',
  },
  {
    n: '03',
    title: 'Walk',
    body: 'Run the Shortcut whenever, or schedule it as a Personal Automation. Your number shows up on the feed within the second.',
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen text-foreground">
      {/* Top bar */}
      <header className="border-b border-border/60 backdrop-blur-md bg-background/70 sticky top-0 z-10">
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
              to="/feed"
              className="label-mono text-muted-foreground hover:text-foreground hidden sm:inline transition-colors"
            >
              Feed
            </Link>
            <Link
              to="/leaderboard"
              className="label-mono text-muted-foreground hover:text-foreground hidden sm:inline transition-colors"
            >
              Leaderboard
            </Link>
            <Link
              to="/join"
              className="label-mono text-muted-foreground hover:text-foreground transition-colors"
            >
              Join
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main>
        {/* HERO */}
        <section className="relative overflow-hidden">
          {/* Decorative tide curve floating in the top-right of the hero */}
          <div
            aria-hidden="true"
            className="absolute -top-12 right-0 w-[60%] sm:w-[45%] text-primary/40 pointer-events-none rise rise-1"
          >
            <WaveCurve shape="tide" className="h-32 sm:h-40" />
          </div>
          <div className="relative max-w-6xl mx-auto px-6 sm:px-8 pt-24 sm:pt-32 pb-24 sm:pb-40">
            {/* Section marker */}
            <div className="flex items-center gap-3 rise rise-1">
              <span className="hairline w-12" />
              <span className="label-mono text-muted-foreground">
                Issue 02 · Public beta
              </span>
            </div>

            <h1 className="mt-10 font-display text-foreground text-[3.25rem] sm:text-[5.5rem] leading-[0.95] tracking-tight max-w-4xl rise rise-2">
              Your steps.
              <br />
              The whole feed{' '}
              <em className="text-primary font-display glow-primary">sees</em>{' '}
              them.
            </h1>

            <p className="mt-8 text-lg sm:text-xl text-muted-foreground max-w-2xl leading-relaxed rise rise-3">
              synzoia is a public step tracker. Pick a username, paste a token
              into an iOS Shortcut, and your daily count posts itself.
              Everyone else’s posts too. No followers. No friend graphs. Just
              steps, ranked, every day.
            </p>

            <div className="mt-12 flex flex-wrap items-center gap-5 rise rise-4">
              <Button variant="primary" to="/join">
                Get started
              </Button>
              <Link
                to="/feed"
                className="label-mono text-muted-foreground hover:text-foreground border-b border-transparent hover:border-foreground transition-colors pb-0.5"
              >
                See today’s feed →
              </Link>
            </div>

            {/* Footer notes inside hero */}
            <div className="mt-20 grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-4 max-w-3xl rise rise-5">
              {[
                ['Source', 'Apple Health'],
                ['Posts', 'Public'],
                ['Feed', 'Chronological'],
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
                  More than a{' '}
                  <em className="text-primary">step counter.</em>
                </h2>
                <p className="text-muted-foreground mt-4 max-w-xl">
                  Apple Health counts your steps. We make them everyone’s
                  business — the small, daily check-in you didn’t know your
                  friends would actually open.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-px bg-border/60 border border-border/60">
              {features.map((f) => (
                <article
                  key={f.n}
                  className="bg-card p-8 sm:p-10 group transition-colors hover:bg-accent/30"
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
                  Three steps to a count that everyone{' '}
                  <em>can see.</em>
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
              Section 04 · Now in public beta
            </span>
            <p className="mt-10 font-display italic text-4xl sm:text-6xl leading-[1.05] tracking-tight">
              “If your phone is already counting,
              <br />
              <span className="text-primary">everyone</span> should see the
              number.”
            </p>
            <p className="mt-8 label-mono text-muted-foreground">
              — what synzoia is built around
            </p>

            <div className="mt-14 flex items-center justify-center">
              <Button variant="primary" to="/join">
                Get your token
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
              Public by default.
            </p>
          </div>
          <div>
            <div className="label-mono text-muted-foreground mb-3">Product</div>
            <ul className="space-y-2">
              <li>
                <Link to="/join" className="hover:text-primary transition-colors">
                  Get started
                </Link>
              </li>
              <li>
                <Link to="/feed" className="hover:text-primary transition-colors">
                  Today’s feed
                </Link>
              </li>
              <li>
                <Link
                  to="/leaderboard"
                  className="hover:text-primary transition-colors"
                >
                  Leaderboard
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
              <li>Cormorant Garamond · Plus Jakarta Sans · Space Mono</li>
              <li>© {new Date().getFullYear()} synzoia</li>
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
}
