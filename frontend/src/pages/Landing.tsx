import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Button from '@/components/ui/AppButton';
import ThemeToggle from '@/components/layout/ThemeToggle';
import WaveCurve from '@/components/ui/WaveCurve';
import { getGlobalSummary } from '@/api/steps';
import { getGlobalSleepSummary } from '@/api/sleep';

// ─── helpers ──────────────────────────────────────────────────────────────────

function fmtSteps(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
}

function fmtMinutes(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h}h ${m}m`;
}

// ─── features data ────────────────────────────────────────────────────────────

const features = [
  {
    n: '01',
    icon: '🚶',
    iconBg: 'bg-[var(--color-primary)]/10',
    accentVar: '--primary',
    title: 'Steps & movement',
    body:
      'A Siri Shortcut reads your Apple Health step count and posts it automatically. Set it once — your daily count lives on the shared feed forever.',
    tag: 'Auto-sync',
  },
  {
    n: '02',
    icon: '🌙',
    iconBg: 'bg-[var(--fern-light)]',
    accentVar: '--fern',
    title: 'Sleep tracking',
    body:
      'Nightly breakdown posted each morning. See how your rest compares across the whole community — deep, core, REM, awake.',
    tag: 'Nightly',
  },
  {
    n: '03',
    icon: '📡',
    iconBg: 'bg-[var(--color-primary)]/10',
    accentVar: '--primary',
    title: 'Universal public feed',
    body:
      'Every post from every user in reverse-chronological order. No algorithm. No friend graph. No curation. Just everyone showing up.',
    tag: 'Realtime',
  },
  {
    n: '04',
    icon: '🏆',
    iconBg: 'bg-[var(--bark-light)]',
    accentVar: '--bark',
    title: 'Three leaderboards',
    body:
      "Today's leader. The week's grinder. The all-time best. Clean, ranked, honest. The kind of table you want your name on.",
    tag: 'Daily reset',
  },
  {
    n: '05',
    icon: '👤',
    iconBg: 'bg-[var(--fern-light)]',
    accentVar: '--fern',
    title: 'Per-user profiles',
    body:
      'Total steps. Best day. Current rank. Days active. The minimum viable record of who has been showing up, and how much.',
    tag: 'Public',
  },
];

// ─── how-it-works data ────────────────────────────────────────────────────────

const howSteps = [
  {
    n: '01',
    title: 'Pick a username',
    body: 'Type one in. We hand you a token — four blocks of uppercase letters. Your key to the whole platform. Paste it into the iOS Shortcut.',
  },
  {
    n: '02',
    title: 'Install the Shortcut',
    body: 'One tap on iPhone. Paste your token. The Shortcut reads Apple Health — steps, sleep — and posts automatically on your behalf.',
  },
  {
    n: '03',
    title: 'Your data posts to the shared feed',
    body: 'Walk. Sleep. Your numbers appear in real time on the public feed. Comment, react, watch each other grow — no algorithm, no feed manipulation.',
  },
];

// ─── StatSkeleton ─────────────────────────────────────────────────────────────

function StatSkeleton() {
  return (
    <div className="flex-1 px-5 py-4 animate-pulse">
      <div className="h-7 w-16 rounded bg-border/60 mb-2" />
      <div className="h-2.5 w-20 rounded bg-border/40" />
    </div>
  );
}

// ─── Landing ──────────────────────────────────────────────────────────────────

export default function Landing() {
  const stepsQ = useQuery({
    queryKey: ['steps', 'summary'],
    queryFn: getGlobalSummary,
    staleTime: 60_000,
  });

  const sleepQ = useQuery({
    queryKey: ['sleep', 'summary'],
    queryFn: getGlobalSleepSummary,
    staleTime: 60_000,
  });

  const statsLoading = stepsQ.isLoading || sleepQ.isLoading;
  const statsError = stepsQ.isError;

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* ── STICKY NAV ───────────────────────────────────────────────────────── */}
      <nav
        className="sticky top-0 z-50 border-b border-border/60"
        style={{
          background:
            'color-mix(in oklch, var(--background) 85%, transparent)',
          backdropFilter: 'blur(20px) saturate(150%)',
        }}
      >
        <div className="max-w-6xl mx-auto px-6 sm:px-8 h-[68px] flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="font-display italic text-[26px] tracking-tight leading-none">
            syn<span className="text-primary">z</span>oia
          </Link>

          {/* Nav links */}
          <ul className="hidden sm:flex items-center gap-8 list-none">
            {[
              { label: 'Features', href: '#features' },
              { label: 'How it works', href: '#how' },
              { label: 'Feed', href: '/feed', internal: true },
            ].map(({ label, href, internal }) =>
              internal ? (
                <li key={label}>
                  <Link
                    to={href}
                    className="label-mono text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {label}
                  </Link>
                </li>
              ) : (
                <li key={label}>
                  <a
                    href={href}
                    className="label-mono text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {label}
                  </a>
                </li>
              ),
            )}
          </ul>

          {/* CTA */}
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <Button variant="primary" to="/feed" className="rounded-full text-sm px-5 py-2">
              Open the feed
            </Button>
          </div>
        </div>
      </nav>

      <main>
        {/* ── HERO ─────────────────────────────────────────────────────────── */}
        <section className="relative overflow-hidden">
          {/* Decorative wave */}
          <div
            aria-hidden="true"
            className="absolute -top-12 right-0 w-[60%] sm:w-[45%] text-primary/40 pointer-events-none rise rise-1"
          >
            <WaveCurve shape="tide" className="h-32 sm:h-40" />
          </div>

          <div className="relative max-w-6xl mx-auto px-6 sm:px-8 pt-24 sm:pt-32 pb-24 sm:pb-40">
            {/* Eyebrow */}
            <div className="flex items-center gap-3 rise rise-1">
              <span className="hairline w-10 bg-primary" style={{ height: '1.5px', background: 'var(--primary)' }} />
              <span className="label-mono text-primary">
                Santa Cruz · Est. 2026 · Public Beta
              </span>
            </div>

            {/* Headline */}
            <h1 className="mt-8 font-display text-foreground text-[3.25rem] sm:text-[5.5rem] leading-[1.0] tracking-tight max-w-3xl rise rise-2">
              Your whole health story.{' '}
              <em className="text-primary glow-primary">Wide open.</em>
            </h1>

            {/* Sub */}
            <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-[520px] leading-relaxed font-light rise rise-3">
              Sleep and steps — tracked automatically via your iOS Shortcut,
              shared openly on one universal feed. A community built on showing
              up, every single day.
            </p>

            {/* Actions */}
            <div className="mt-10 flex flex-wrap items-center gap-5 rise rise-4">
              <Button variant="primary" to="/feed">
                Open the feed
              </Button>
              <Link
                to="/join"
                className="label-mono text-muted-foreground hover:text-foreground border-b border-border hover:border-foreground transition-colors pb-0.5"
              >
                Get your token →
              </Link>
            </div>

            {/* Live stat bar */}
            <div
              className="mt-16 max-w-[680px] border border-border overflow-hidden rise rise-5"
              style={{
                borderRadius: '1.25rem',
                background:
                  'color-mix(in oklch, var(--card) 85%, transparent)',
                backdropFilter: 'blur(12px)',
              }}
            >
              {statsError ? (
                <div className="px-6 py-4 label-mono text-muted-foreground">
                  Could not load live stats — try refreshing.
                </div>
              ) : (
                <div className="flex divide-x divide-border">
                  {/* Walkers */}
                  {statsLoading ? (
                    <StatSkeleton />
                  ) : (
                    <div className="flex-1 px-5 py-4">
                      <div className="font-display text-[2rem] leading-none tracking-tight">
                        {stepsQ.data ? stepsQ.data.total_users.toLocaleString() : '—'}
                      </div>
                      <div className="label-mono text-muted-foreground mt-1">
                        Active walkers
                      </div>
                    </div>
                  )}

                  {/* All-time steps */}
                  {statsLoading ? (
                    <StatSkeleton />
                  ) : (
                    <div className="flex-1 px-5 py-4">
                      <div className="font-display text-[2rem] leading-none tracking-tight">
                        {stepsQ.data
                          ? fmtSteps(stepsQ.data.total_steps_all_time)
                          : '—'}
                      </div>
                      <div className="label-mono text-muted-foreground mt-1">
                        All-time steps
                      </div>
                    </div>
                  )}

                  {/* This week's leader */}
                  {statsLoading ? (
                    <StatSkeleton />
                  ) : (
                    <div className="flex-1 px-5 py-4">
                      <div className="font-display text-[2rem] leading-none tracking-tight truncate">
                        {stepsQ.data?.this_week_leader?.username ?? '—'}
                      </div>
                      <div className="label-mono text-muted-foreground mt-1">
                        Week leader
                      </div>
                    </div>
                  )}

                  {/* Avg sleep (global) */}
                  {statsLoading ? (
                    <StatSkeleton />
                  ) : (
                    <div className="flex-1 px-5 py-4">
                      <div className="font-display text-[2rem] leading-none tracking-tight">
                        {sleepQ.data
                          ? fmtMinutes(sleepQ.data.avg_duration_min)
                          : stepsQ.data?.best_day_ever
                            ? fmtSteps(stepsQ.data.best_day_ever.total)
                            : '—'}
                      </div>
                      <div className="label-mono text-muted-foreground mt-1">
                        {sleepQ.data ? 'Avg sleep' : 'Best day ever'}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ── FEATURES GRID ────────────────────────────────────────────────── */}
        <section id="features" className="border-t border-border bg-secondary/30">
          <div className="max-w-6xl mx-auto px-6 sm:px-8 py-24 sm:py-32">
            {/* Section header */}
            <div className="mb-14">
              <div className="flex items-center gap-3 mb-5">
                <span className="label-mono text-muted-foreground">— Section 01</span>
              </div>
              <h2 className="font-display text-[2.25rem] sm:text-[3.5rem] leading-tight tracking-tight">
                More than a tracker.{' '}
                <em className="text-primary">A living record.</em>
              </h2>
              <p className="mt-4 text-muted-foreground max-w-[560px] leading-relaxed font-light">
                Steps and sleep. A shared feed. A leaderboard. The minimum
                viable stack for a community built on showing up.
              </p>
            </div>

            {/* Grid */}
            <div
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-border/60 border border-border/60"
              style={{ borderRadius: '1.25rem', overflow: 'hidden' }}
            >
              {features.map((f) => (
                <article
                  key={f.n}
                  className="bg-card p-8 sm:p-9 group transition-colors hover:bg-accent/30 relative"
                  style={{
                    borderLeft: `3px solid var(${f.accentVar})`,
                  }}
                >
                  {/* Icon */}
                  <div
                    className={`w-11 h-11 rounded-xl flex items-center justify-center mb-5 text-xl ${f.iconBg}`}
                  >
                    {f.icon}
                  </div>

                  {/* Number */}
                  <div className="label-mono text-muted-foreground mb-2">
                    {f.n}
                  </div>

                  {/* Title */}
                  <h3 className="font-display text-2xl tracking-tight text-foreground mb-2 leading-snug">
                    {f.title}
                  </h3>

                  {/* Desc */}
                  <p className="text-sm text-muted-foreground leading-relaxed font-light">
                    {f.body}
                  </p>

                  {/* Tag */}
                  <span
                    className="inline-block mt-4 px-3 py-1 rounded-full label-mono text-primary"
                    style={{ background: 'color-mix(in oklch, var(--primary) 10%, transparent)' }}
                  >
                    {f.tag}
                  </span>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ── HOW IT WORKS ─────────────────────────────────────────────────── */}
        <section id="how" className="border-t border-border bg-background">
          <div className="max-w-6xl mx-auto px-6 sm:px-8 py-24 sm:py-32">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-16 sm:gap-24 items-start">
              {/* Left col */}
              <div>
                <div className="flex items-center gap-3 mb-5">
                  <span className="label-mono text-muted-foreground">— Section 02 · Setup</span>
                </div>
                <h2 className="font-display text-[2.25rem] sm:text-[3.5rem] leading-tight tracking-tight">
                  Three steps to a life{' '}
                  <em className="text-primary">in the open.</em>
                </h2>
              </div>

              {/* Right col — steps list */}
              <ol className="divide-y divide-border">
                {howSteps.map((s) => (
                  <li key={s.n} className="grid grid-cols-[80px_1fr] gap-0 py-10 first:pt-0 last:pb-0">
                    <div
                      className="font-display italic text-[64px] font-light leading-none pt-1"
                      style={{
                        color: 'color-mix(in oklch, var(--bark) 35%, var(--border))',
                      }}
                    >
                      {s.n}
                    </div>
                    <div>
                      <h3 className="font-display text-[1.875rem] tracking-tight text-foreground mb-2 leading-snug">
                        {s.title}
                      </h3>
                      <p className="text-[0.9375rem] text-muted-foreground leading-relaxed font-light max-w-[540px]">
                        {s.body}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        {/* ── CTA BAND ─────────────────────────────────────────────────────── */}
        <section className="forest-band surface-grain border-t border-border/20">
          <div className="relative max-w-4xl mx-auto px-6 sm:px-8 py-28 sm:py-36 text-center">
            <div className="flex items-center justify-center gap-3 mb-10">
              <span
                className="label-mono"
                style={{ color: 'var(--primary)', opacity: 0.9 }}
              >
                — Public Beta · Free to join
              </span>
            </div>

            <p
              className="font-display italic leading-[1.15] tracking-tight"
              style={{
                fontSize: 'clamp(2rem, 5vw, 3.625rem)',
                color: 'oklch(0.9620 0.0180 80)',
              }}
            >
              "If you're already living it,
              <br />
              you might as well let{' '}
              <span className="text-primary not-italic">everyone</span> see."
            </p>

            <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
              <Button
                variant="primary"
                to="/feed"
                className="rounded-full bg-[oklch(0.9620_0.0180_80)] text-[var(--fern-deep)] hover:bg-[oklch(0.96_0.018_80)/90] font-semibold"
              >
                Open the feed →
              </Button>
              <Link
                to="/join"
                className="label-mono border border-[oklch(0.9620_0.0180_80)/40] text-[oklch(0.9620_0.0180_80)] px-6 py-2.5 rounded-full hover:border-[oklch(0.9620_0.0180_80)] transition-colors"
              >
                Get your token
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* ── FOOTER ───────────────────────────────────────────────────────────── */}
      <footer className="border-t border-border bg-secondary/30">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 pt-14 pb-10">
          {/* Main grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-12 pb-10 border-b border-border">
            {/* Brand */}
            <div className="col-span-2">
              <Link to="/" className="font-display italic text-[1.75rem] tracking-tight">
                syn<span className="text-primary">z</span>oia
              </Link>
              <p className="label-mono text-muted-foreground mt-3 leading-relaxed">
                Public by default.
                <br />
                Santa Cruz, California.
                <br />
                Est. 2026.
              </p>
            </div>

            {/* Product links */}
            <div>
              <div className="label-mono text-muted-foreground mb-4">Product</div>
              <ul className="space-y-2 text-sm font-light text-muted-foreground">
                <li>
                  <Link to="/join" className="hover:text-foreground transition-colors">
                    Get started
                  </Link>
                </li>
                <li>
                  <Link to="/feed" className="hover:text-foreground transition-colors">
                    Live feed
                  </Link>
                </li>
                <li>
                  <Link to="/leaderboard" className="hover:text-foreground transition-colors">
                    Leaderboard
                  </Link>
                </li>
              </ul>
            </div>

            {/* Community links */}
            <div>
              <div className="label-mono text-muted-foreground mb-4">Community</div>
              <ul className="space-y-2 text-sm font-light text-muted-foreground">
                <li>
                  <a href="#how" className="hover:text-foreground transition-colors">
                    How it works
                  </a>
                </li>
                <li>
                  <a href="#features" className="hover:text-foreground transition-colors">
                    Features
                  </a>
                </li>
                <li>
                  <Link to="/style-guide" className="hover:text-foreground transition-colors">
                    Style guide
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          {/* Bottom bar */}
          <div className="pt-7 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <span className="label-mono text-muted-foreground">
              Cormorant Garamond · Plus Jakarta Sans · Space Mono · © {new Date().getFullYear()} synzoia
            </span>
            <span className="label-mono text-muted-foreground">
              Public by default. No algorithm. No ads.
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
