import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import FormField from '@/components/ui/FormField';
import PageHeader from '@/components/ui/PageHeader';
import EmptyState from '@/components/ui/EmptyState';
import TabStrip from '@/components/ui/TabStrip';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import type { ReactNode } from 'react';

const tokens = [
  'background',
  'foreground',
  'card',
  'card-foreground',
  'popover',
  'popover-foreground',
  'primary',
  'primary-foreground',
  'secondary',
  'secondary-foreground',
  'muted',
  'muted-foreground',
  'accent',
  'accent-foreground',
  'destructive',
  'destructive-foreground',
  'border',
  'input',
  'ring',
];

function ColorSwatch({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="w-10 h-10 rounded-md border border-border"
        style={{ backgroundColor: `var(--${name})` }}
      />
      <code className="text-xs text-muted-foreground">--{name}</code>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold tracking-tight text-foreground">{title}</h2>
      <Separator />
      <div>{children}</div>
    </section>
  );
}

export function StyleGuide() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-2xl font-semibold tracking-tight">synzoia style guide</h1>
        <p className="text-muted-foreground text-sm">v1 — ocean-breeze theme</p>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10 space-y-16">
        <Section title="Brand">
          <p className="text-muted-foreground text-sm">
            Wordmark: <span className="text-foreground font-semibold">synzoia</span>.
            Logo asset lands separately; placeholder is the plain text wordmark.
          </p>
        </Section>

        <Section title="Colors">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Reflects current OS appearance (light or dark). Toggle your system theme to see the other palette.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {tokens.map((t) => (
                <ColorSwatch key={t} name={t} />
              ))}
            </div>
          </div>
        </Section>

        <Section title="Typography">
          <div className="space-y-3">
            <h1 className="text-4xl font-bold tracking-tight">H1 — Display</h1>
            <h2 className="text-2xl font-semibold tracking-tight">H2 — Section</h2>
            <h3 className="text-lg font-semibold">H3 — Subsection</h3>
            <p className="text-base">Body — default text on background.</p>
            <p className="text-sm text-muted-foreground">Muted — secondary info.</p>
            <p className="text-xs text-muted-foreground">Caption — metadata.</p>
          </div>
        </Section>

        <Section title="Radii">
          <div className="flex gap-4">
            <div className="w-20 h-20 bg-primary rounded-sm" />
            <div className="w-20 h-20 bg-primary rounded-md" />
            <div className="w-20 h-20 bg-primary rounded-lg" />
            <div className="w-20 h-20 bg-primary rounded-xl" />
          </div>
        </Section>

        <Section title="Buttons">
          <div className="flex flex-wrap gap-3">
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="primary" disabled>
              Primary disabled
            </Button>
            <Button variant="secondary" disabled>
              Secondary disabled
            </Button>
            <Button variant="primary" to="/style-guide">
              Primary as link
            </Button>
          </div>
        </Section>

        <Section title="Cards">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Card>
              <h3 className="text-lg font-semibold">Simple card</h3>
              <p className="text-muted-foreground text-sm mt-1">
                One-slot card with default padding.
              </p>
            </Card>
            <Card className="bg-muted">
              <h3 className="text-lg font-semibold">Muted card</h3>
              <p className="text-muted-foreground text-sm mt-1">
                Same component, muted surface variant via className.
              </p>
            </Card>
          </div>
        </Section>

        <Section title="Form fields">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-xl">
            <FormField id="sg-email" label="Email" type="email" placeholder="you@example.com" />
            <FormField
              id="sg-bad"
              label="With error"
              type="text"
              error="Required"
              defaultValue=""
            />
            <FormField id="sg-disabled" label="Disabled" type="text" disabled />
            <FormField id="sg-number" label="Number" type="number" min={1} max={100} />
          </div>
        </Section>

        <Section title="Tabs">
          <TabStrip
            paramName="sgtab"
            defaultKey="feed"
            tabs={[
              { key: 'feed', label: 'Feed' },
              { key: 'leaderboard', label: 'Leaderboard' },
              { key: 'chat', label: 'Chat' },
            ]}
          />
        </Section>

        <Section title="Empty states">
          <Card>
            <EmptyState />
          </Card>
          <div className="h-4" />
          <Card>
            <EmptyState message="Custom message — feed empty for this crew." />
          </Card>
        </Section>

        <Section title="Badges">
          <div className="flex flex-wrap gap-2">
            <Badge>Default</Badge>
            <Badge variant="secondary">Secondary</Badge>
            <Badge variant="destructive">Destructive</Badge>
            <Badge variant="outline">Outline</Badge>
          </div>
        </Section>

        <Section title="Avatars">
          <div className="flex gap-3">
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
          </div>
        </Section>

        <Section title="Page header (in context)">
          <PageHeader
            title="Example page"
            description="This is what PageHeader renders inline."
            action={<Button variant="primary">Action</Button>}
          />
        </Section>
      </main>
    </div>
  );
}

export default StyleGuide;
