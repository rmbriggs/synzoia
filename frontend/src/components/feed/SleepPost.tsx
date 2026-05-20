import { Link } from 'react-router-dom';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  formatClock,
  getUser,
  relativeTime,
  type SleepPost as SleepPostT,
} from '@/lib/mockData';

export default function SleepPost({ post }: { post: SleepPostT }) {
  const user = getUser(post.userId);
  if (!user) return null;

  return (
    <article className="border-b border-border py-6 first:pt-0 last:border-b-0">
      <div className="flex items-start gap-4">
        <Link to={`/users/${user.id}`} className="shrink-0">
          <Avatar>
            <AvatarFallback>{user.initials}</AvatarFallback>
          </Avatar>
        </Link>

        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between gap-2 flex-wrap">
            <div className="flex items-baseline gap-3">
              <Link
                to={`/users/${user.id}`}
                className="font-display italic text-lg hover:text-primary transition-colors"
              >
                {user.displayName}
              </Link>
              <span className="label-mono text-muted-foreground">
                {relativeTime(post.postedAt)}
              </span>
            </div>
            <span className="font-display italic text-xl text-primary tabular-nums">
              {post.hours.toFixed(1)}h
            </span>
          </div>

          <div className="mt-2 flex items-center gap-4 label-mono text-muted-foreground">
            <span>
              <span className="text-foreground">{formatClock(post.bedtime)}</span>
              <span className="opacity-60"> · bed</span>
            </span>
            <span className="opacity-30">→</span>
            <span>
              <span className="text-foreground">{formatClock(post.wake)}</span>
              <span className="opacity-60"> · wake</span>
            </span>
            <span className="opacity-30">·</span>
            <span>q{post.quality}</span>
          </div>

          {post.note && (
            <p className="mt-3 text-foreground leading-relaxed">{post.note}</p>
          )}

          {post.reactions.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {post.reactions.map((r) => (
                <span
                  key={r.emoji}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted text-sm border border-border"
                >
                  <span>{r.emoji}</span>
                  <span className="label-mono text-muted-foreground">
                    {r.count}
                  </span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
