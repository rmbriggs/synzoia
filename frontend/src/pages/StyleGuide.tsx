import { Link } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import FormField from '@/components/ui/FormField';
import PageHeader from '@/components/ui/PageHeader';
import EmptyState from '@/components/ui/EmptyState';
import TabStrip from '@/components/ui/TabStrip';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import type { ReactNode } from 'react';

const colorTokens = [
  { name: 'background', role: 'Page surface' },
  { name: 'foreground', role: 'Default text' },
  { name: 'card', role: 'Card surface' },
  { name: 'card-foreground', role: 'Card text' },
  { name: 'primary', role: 'Accent / CTA' },
  { name: 'primary-foreground', role: 'On primary' },
  { name: 'secondary', role: 'Soft surface' },
  { name: 'secondary-foreground', role: 'On secondary' },
  { name: 'muted', role: 'Quiet surface' },
  { name: 'muted-foreground', role: 'Secondary text' },
  { name: 'accent', role: 'Highlight' },
  { name: 'accent-foreground', role: 'On accent' },
  { name: 'destructive', role: 'Danger' },
  { name: 'destructive-foreground', role: 'On danger' },
  { name: 'border', role: 'Hairlines' },
  { name: 'input', role: 'Field border' },
  { name: 'ring', role: 'Focus ring' },
];

type SpreadProps = {
  n: string;
  title: string;
  kicker?: string;
  children: ReactNode;
};

function Spread({ n, title, kicker, children }: SpreadProps) {
  return (
    <section className="border-t border-border">
      <div className="max-w-6xl mx-auto px-6 sm:px-10 py-20 sm:py-28">
        <div className="grid grid-cols-12 gap-x-6 gap-y-6 mb-12 sm:mb-16">
          <div className="col-span-12 sm:col-span-3">
            <div className="flex items-baseline gap-3">
              <span className="font-display italic text-5xl text-primary leading-none">
                {n}
              </span>
              <span className="hairline w-12" />
            </div>
          </div>
          <div className="col-span-12 sm:col-span-9">
            {kicker && (
              <div className="label-mono text-muted-foreground mb-3">{kicker}</div>
            )}
            <h2 className="font-display text-3xl sm:text-5xl tracking-tight leading-tight">
              {title}
            </h2>
          </div>
        </div>
        <div>{children}</div>
      </div>
    </section>
  );
}

function Swatch({ name, role }: { name: string; role: string }) {
  return (
    <div className="border border-border bg-background">
      <div
        className="aspect-[5/3] w-full"
        style={{ backgroundColor: `var(--${name})` }}
      />
      <div className="p-4 space-y-2">
        <div className="font-display italic text-lg leading-none">{role}</div>
        <div className="label-mono text-muted-foreground">--{name}</div>
      </div>
    </div>
  );
}

export default function StyleGuide() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* MASTHEAD */}
      <header className="border-b border-border">
        <div className="max-w-6xl mx-auto px-6 sm:px-10 py-8 sm:py-12">
          <div className="flex items-center justify-between mb-10">
            <Link
              to="/"
              className="label-mono text-muted-foreground hover:text-foreground transition-colors"
            >
              ← Back to home
            </Link>
            <span className="label-mono text-muted-foreground">v1 · 2026</span>
          </div>

          <div className="grid grid-cols-12 gap-x-6 gap-y-4">
            <div className="col-span-12 sm:col-span-3">
              <span
                data-logo-slot
                className="font-display italic text-3xl tracking-tight"
              >
                synzoia
              </span>
              <div className="label-mono text-muted-foreground mt-3">
                The colophon
              </div>
            </div>
            <div className="col-span-12 sm:col-span-9">
              <h1 className="font-display text-5xl sm:text-7xl leading-[0.95] tracking-tight">
                A field guide to the
                <br />
                <em className="text-primary">visual language</em>.
              </h1>
              <p className="text-muted-foreground mt-6 max-w-xl leading-relaxed">
                Every token, type face, and primitive that makes up the synzoia
                interface — set out plain, with names attached.
              </p>
            </div>
          </div>
        </div>
      </header>

      <main>
        <Spread n="01" kicker="Palette · Ocean-breeze" title="The colours.">
          <p className="text-muted-foreground max-w-2xl mb-8">
            All tokens render in the current OS appearance. Flip your system to
            dark to see the night palette — every name maps the same way, the
            values change.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {colorTokens.map((t) => (
              <Swatch key={t.name} name={t.name} role={t.role} />
            ))}
          </div>
        </Spread>

        <Spread n="02" kicker="Three faces" title="The typography.">
          <div className="grid grid-cols-12 gap-x-6 gap-y-12">
            <div className="col-span-12 lg:col-span-4">
              <div className="label-mono text-muted-foreground mb-2">Display</div>
              <div className="font-display text-6xl leading-none">Aa</div>
              <div className="font-display italic text-6xl leading-none mt-1 text-primary">
                Aa
              </div>
              <div className="mt-4 space-y-1">
                <div className="font-display text-xl">Lora</div>
                <div className="label-mono text-muted-foreground">
                  Serif · 400 / 500 / 600 / italic
                </div>
              </div>
            </div>
            <div className="col-span-12 lg:col-span-4">
              <div className="label-mono text-muted-foreground mb-2">Body</div>
              <div className="text-6xl leading-none">Aa</div>
              <div className="text-6xl leading-none mt-1 text-primary">Aa</div>
              <div className="mt-4 space-y-1">
                <div className="text-xl font-medium">DM Sans</div>
                <div className="label-mono text-muted-foreground">
                  Sans · 400 / 500 / 600 / 700
                </div>
              </div>
            </div>
            <div className="col-span-12 lg:col-span-4">
              <div className="label-mono text-muted-foreground mb-2">Numeric</div>
              <div className="font-mono text-6xl leading-none">Aa</div>
              <div className="font-mono text-6xl leading-none mt-1 text-primary">
                01
              </div>
              <div className="mt-4 space-y-1">
                <div className="font-mono text-xl">IBM Plex Mono</div>
                <div className="label-mono text-muted-foreground">
                  Mono · 400 / 500 / 600
                </div>
              </div>
            </div>
          </div>

          <div className="hairline my-12" />

          <div className="space-y-6">
            <div className="grid grid-cols-12 gap-x-6 items-baseline">
              <span className="col-span-12 sm:col-span-2 label-mono text-muted-foreground">
                Display · 5xl
              </span>
              <span className="col-span-12 sm:col-span-10 font-display text-5xl italic">
                A late-night ritual.
              </span>
            </div>
            <div className="grid grid-cols-12 gap-x-6 items-baseline">
              <span className="col-span-12 sm:col-span-2 label-mono text-muted-foreground">
                H2 · 3xl
              </span>
              <span className="col-span-12 sm:col-span-10 font-display text-3xl">
                The group chat that turns into a habit.
              </span>
            </div>
            <div className="grid grid-cols-12 gap-x-6 items-baseline">
              <span className="col-span-12 sm:col-span-2 label-mono text-muted-foreground">
                H3 · xl
              </span>
              <span className="col-span-12 sm:col-span-10 text-xl font-semibold">
                Reactions and the thread
              </span>
            </div>
            <div className="grid grid-cols-12 gap-x-6 items-baseline">
              <span className="col-span-12 sm:col-span-2 label-mono text-muted-foreground">
                Body · base
              </span>
              <span className="col-span-12 sm:col-span-10">
                Default body text — used for most product copy, paragraphs, and
                supporting prose throughout the application.
              </span>
            </div>
            <div className="grid grid-cols-12 gap-x-6 items-baseline">
              <span className="col-span-12 sm:col-span-2 label-mono text-muted-foreground">
                Muted · sm
              </span>
              <span className="col-span-12 sm:col-span-10 text-sm text-muted-foreground">
                Secondary information — captions, helper text, metadata.
              </span>
            </div>
            <div className="grid grid-cols-12 gap-x-6 items-baseline">
              <span className="col-span-12 sm:col-span-2 label-mono text-muted-foreground">
                Mono label
              </span>
              <span className="col-span-12 sm:col-span-10 label-mono text-muted-foreground">
                Section labels · timestamps · numerals
              </span>
            </div>
          </div>
        </Spread>

        <Spread n="03" kicker="Primitives" title="The buttons.">
          <div className="grid grid-cols-12 gap-x-6 gap-y-10">
            <div className="col-span-12 sm:col-span-3">
              <div className="label-mono text-muted-foreground">Variants</div>
            </div>
            <div className="col-span-12 sm:col-span-9 flex flex-wrap gap-3">
              <Button variant="primary">Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="ghost">Ghost</Button>
            </div>

            <div className="col-span-12 sm:col-span-3">
              <div className="label-mono text-muted-foreground">Disabled</div>
            </div>
            <div className="col-span-12 sm:col-span-9 flex flex-wrap gap-3">
              <Button variant="primary" disabled>
                Primary
              </Button>
              <Button variant="secondary" disabled>
                Secondary
              </Button>
              <Button variant="ghost" disabled>
                Ghost
              </Button>
            </div>

            <div className="col-span-12 sm:col-span-3">
              <div className="label-mono text-muted-foreground">As link</div>
            </div>
            <div className="col-span-12 sm:col-span-9 flex flex-wrap gap-3">
              <Button variant="primary" to="/style-guide">
                Primary →
              </Button>
              <Button variant="secondary" to="/style-guide">
                Secondary →
              </Button>
            </div>
          </div>
        </Spread>

        <Spread n="04" kicker="Primitives" title="The cards.">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <Card>
              <div className="label-mono text-muted-foreground mb-2">Simple</div>
              <h3 className="font-display text-2xl tracking-tight">
                One-slot card
              </h3>
              <p className="text-muted-foreground text-sm mt-2 leading-relaxed">
                Default surface with comfortable padding. The workhorse of the
                interface — feed posts, settings sections, empty states.
              </p>
            </Card>
            <Card className="bg-muted">
              <div className="label-mono text-muted-foreground mb-2">Muted</div>
              <h3 className="font-display text-2xl tracking-tight">
                Quiet variant
              </h3>
              <p className="text-muted-foreground text-sm mt-2 leading-relaxed">
                Same component, restated against a muted surface for visual
                rhythm or to deemphasise auxiliary content.
              </p>
            </Card>
          </div>
        </Spread>

        <Spread n="05" kicker="Primitives" title="The fields.">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-3xl">
            <FormField
              id="sg-email"
              label="Email"
              type="email"
              placeholder="you@crew.so"
            />
            <FormField
              id="sg-bad"
              label="With error"
              type="text"
              error="This is required"
              defaultValue=""
            />
            <FormField id="sg-disabled" label="Disabled" type="text" disabled />
            <FormField
              id="sg-number"
              label="Quality (1–100)"
              type="number"
              min={1}
              max={100}
              placeholder="78"
            />
          </div>
        </Spread>

        <Spread n="06" kicker="Composition" title="Tabs and empty states.">
          <div className="space-y-10">
            <div>
              <div className="label-mono text-muted-foreground mb-4">
                TabStrip · URL-bound to ?sgtab=
              </div>
              <TabStrip
                paramName="sgtab"
                defaultKey="feed"
                tabs={[
                  { key: 'feed', label: 'Feed' },
                  { key: 'leaderboard', label: 'Leaderboard' },
                  { key: 'chat', label: 'Chat' },
                ]}
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <Card>
                <EmptyState />
              </Card>
              <Card>
                <EmptyState message="No posts yet — your crew is still asleep." />
              </Card>
            </div>
          </div>
        </Spread>

        <Spread n="07" kicker="Atoms" title="Badges and avatars.">
          <div className="grid grid-cols-12 gap-x-6 gap-y-10">
            <div className="col-span-12 sm:col-span-3">
              <div className="label-mono text-muted-foreground">Badges</div>
            </div>
            <div className="col-span-12 sm:col-span-9 flex flex-wrap gap-2">
              <Badge>Default</Badge>
              <Badge variant="secondary">Secondary</Badge>
              <Badge variant="destructive">Destructive</Badge>
              <Badge variant="outline">Outline</Badge>
            </div>

            <div className="col-span-12 sm:col-span-3">
              <div className="label-mono text-muted-foreground">Avatars</div>
            </div>
            <div className="col-span-12 sm:col-span-9 flex flex-wrap gap-3 items-center">
              <Avatar>
                <AvatarImage src="" alt="" />
                <AvatarFallback>MB</AvatarFallback>
              </Avatar>
              <Avatar>
                <AvatarFallback>AB</AvatarFallback>
              </Avatar>
              <Avatar>
                <AvatarFallback>CD</AvatarFallback>
              </Avatar>
              <Avatar>
                <AvatarFallback>EF</AvatarFallback>
              </Avatar>
              <Avatar>
                <AvatarFallback>GH</AvatarFallback>
              </Avatar>
            </div>
          </div>
        </Spread>

        <Spread n="08" kicker="In context" title="A page header.">
          <Card>
            <PageHeader
              title="Crew · The night owls"
              description="Real crew name lands when backend's ready."
              action={<Button variant="primary">Post sleep</Button>}
            />
          </Card>
        </Spread>
      </main>

      <footer
        className="border-t border-border"
        style={{ background: 'var(--foreground)', color: 'var(--background)' }}
      >
        <div className="max-w-6xl mx-auto px-6 sm:px-10 py-16">
          <div className="grid grid-cols-12 gap-x-6 gap-y-6">
            <div className="col-span-12 sm:col-span-6">
              <span className="font-display italic text-4xl">synzoia</span>
              <p className="opacity-70 mt-4 max-w-md">
                The style guide is set in{' '}
                <em className="font-display">Lora</em>, DM Sans, and IBM Plex
                Mono. Colour from the{' '}
                <em className="font-display">ocean-breeze</em> theme by tweakcn.
              </p>
            </div>
            <div className="col-span-12 sm:col-span-6 flex sm:justify-end items-end">
              <Link
                to="/"
                className="label-mono opacity-70 hover:opacity-100 transition-opacity"
              >
                ← Back to home
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
