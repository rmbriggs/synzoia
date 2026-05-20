import { Link } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  formatClock,
  getCurrentUser,
  getLeaderboardForCrew,
  getStreakForUser,
  getUser,
  listCrewsForUser,
  listPostsForCrew,
  listPostsForUser,
  relativeTime,
} from '@/lib/mockData';

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return 'Still up,';
  if (h < 12) return 'Good morning,';
  if (h < 17) return 'Good afternoon,';
  return 'Good evening,';
}

function todayLabel(): string {
  const now = new Date();
  const weekday = now.toLocaleDateString('en-US', { weekday: 'short' });
  const month = now.toLocaleDateString('en-US', { month: 'short' });
  return `${weekday}, ${month} ${now.getDate()}`;
}

function postedWithinLast24h(userId: string): boolean {
  const posts = listPostsForUser(userId, 1);
  if (posts.length === 0) return false;
  const latest = new Date(posts[0].postedAt).getTime();
  return Date.now() - latest < 24 * 60 * 60 * 1000;
}

export default function Dashboard() {
  const me = getCurrentUser();
  const myCrews = listCrewsForUser(me.id);
  const streak = getStreakForUser(me.id);
  const postedToday = postedWithinLast24h(me.id);
  const myLatestPost = listPostsForUser(me.id, 1)[0];

  // Cross-crew feed: latest posts from all of my crews, mixed by time
  const crossCrewFeed = myCrews
    .flatMap((c) => listPostsForCrew(c.id))
    .filter((p) => p.userId !== me.id) // others' nights, not mine
    .sort(
      (a, b) =>
        new Date(b.postedAt).getTime() - new Date(a.postedAt).getTime(),
    )
    .slice(0, 5);

  return (
    <div className="-mx-4 sm:-mx-6 -my-6 sm:-my-6">
      {/* GREETING — washed hero matching the landing */}
      <section className="hero-wash surface-grain border-b border-border">
        <div className="relative px-4 sm:px-6 pt-12 pb-10 sm:pt-16 sm:pb-12 max-w-2xl mx-auto">
          <div className="flex items-center gap-3 rise rise-1">
            <span className="hairline w-12" />
            <span className="label-mono text-muted-foreground">
              Today · {todayLabel()}
            </span>
          </div>

          <h1 className="mt-6 font-display text-5xl sm:text-6xl leading-[0.95] tracking-tight rise rise-2">
            {greeting()}
            <br />
            <em className="text-primary">{me.displayName}.</em>
          </h1>

          {postedToday && myLatestPost ? (
            <div className="mt-8 flex items-baseline gap-3 flex-wrap rise rise-3">
              <span className="label-mono text-muted-foreground">
                You posted ·
              </span>
              <span className="font-display italic text-xl">
                {myLatestPost.hours.toFixed(1)}h
              </span>
              <span className="label-mono text-muted-foreground">·</span>
              <span className="label-mono text-muted-foreground">
                bed {formatClock(myLatestPost.bedtime)}
              </span>
              <span className="label-mono text-muted-foreground">·</span>
              <span className="label-mono text-muted-foreground">
                wake {formatClock(myLatestPost.wake)}
              </span>
              <span className="label-mono text-muted-foreground">·</span>
              <span className="label-mono text-muted-foreground">
                q{myLatestPost.quality}
              </span>
            </div>
          ) : (
            <div className="mt-8 rise rise-3">
              <p className="text-muted-foreground mb-4">
                You haven't posted yet today.
              </p>
              <Button
                variant="primary"
                to={`/crews/${myCrews[0]?.id ?? 'c-owls'}/post`}
              >
                Post sleep
              </Button>
            </div>
          )}
        </div>
      </section>

      <div className="px-4 sm:px-6 py-10 max-w-2xl mx-auto space-y-10">
        {/* STREAK */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="font-display italic text-xl text-primary">01</span>
            <span className="hairline flex-1" />
            <span className="label-mono text-muted-foreground">Streaks</span>
          </div>
          <Card>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <div className="font-display italic text-6xl text-primary tabular-nums leading-none">
                  {streak.current}
                </div>
                <div className="label-mono text-muted-foreground mt-2">
                  current · nights
                </div>
              </div>
              <div>
                <div className="font-display italic text-6xl tabular-nums leading-none">
                  {streak.longest}
                </div>
                <div className="label-mono text-muted-foreground mt-2">
                  longest · nights
                </div>
              </div>
            </div>
          </Card>
        </section>

        {/* CREWS */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="font-display italic text-xl text-primary">02</span>
            <span className="hairline flex-1" />
            <span className="label-mono text-muted-foreground">
              Your crews
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {myCrews.map((crew) => {
              const board = getLeaderboardForCrew(crew.id);
              const myEntry = board.find((e) => e.userId === me.id);
              return (
                <Link
                  key={crew.id}
                  to={`/crews/${crew.id}`}
                  className="block border border-border bg-background hover:bg-accent/30 transition-colors p-5 group"
                >
                  <h3 className="font-display text-xl tracking-tight group-hover:text-primary transition-colors">
                    {crew.name}
                  </h3>
                  <div className="label-mono text-muted-foreground mt-1">
                    {crew.memberIds.length} members
                  </div>
                  <div className="hairline my-4" />
                  {myEntry ? (
                    <div className="flex items-baseline justify-between">
                      <div>
                        <div className="font-display italic text-3xl text-primary tabular-nums leading-none">
                          #{myEntry.rank}
                        </div>
                        <div className="label-mono text-muted-foreground mt-1">
                          your rank · this week
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-mono text-base tabular-nums">
                          {myEntry.hoursThisWeek}h
                        </div>
                        <div className="label-mono text-muted-foreground">
                          slept
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="label-mono text-muted-foreground">
                      No standing yet
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        </section>

        {/* CROSS-CREW FEED */}
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="font-display italic text-xl text-primary">03</span>
            <span className="hairline flex-1" />
            <span className="label-mono text-muted-foreground">
              From your crews
            </span>
          </div>
          <Card>
            {crossCrewFeed.length === 0 ? (
              <p className="text-muted-foreground text-sm py-6 text-center">
                Nothing yet. Wait for your crews to wake up.
              </p>
            ) : (
              <div>
                {crossCrewFeed.map((post) => {
                  const crew = myCrews.find((c) => c.id === post.crewId);
                  const author = getUser(post.userId);
                  if (!author || !crew) return null;
                  return (
                    <article
                      key={post.id}
                      className="border-b border-border py-5 first:pt-0 last:border-b-0"
                    >
                      <div className="flex items-start gap-3">
                        <Link to={`/users/${author.id}`} className="shrink-0">
                          <Avatar>
                            <AvatarFallback>{author.initials}</AvatarFallback>
                          </Avatar>
                        </Link>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-baseline justify-between gap-2 flex-wrap">
                            <div className="flex items-baseline gap-2">
                              <Link
                                to={`/users/${author.id}`}
                                className="font-display italic text-base hover:text-primary transition-colors"
                              >
                                {author.displayName}
                              </Link>
                              <span className="label-mono text-muted-foreground">
                                · in{' '}
                              </span>
                              <Link
                                to={`/crews/${crew.id}`}
                                className="label-mono text-muted-foreground hover:text-foreground transition-colors"
                              >
                                {crew.name}
                              </Link>
                            </div>
                            <span className="label-mono text-muted-foreground">
                              {relativeTime(post.postedAt)}
                            </span>
                          </div>
                          <div className="mt-1.5 flex items-baseline gap-3 label-mono text-muted-foreground">
                            <span className="font-display italic text-primary not-italic text-base">
                              {post.hours.toFixed(1)}h
                            </span>
                            {post.note && (
                              <span className="font-sans text-foreground text-sm leading-relaxed">
                                {post.note}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </Card>
        </section>
      </div>

    </div>
  );
}
