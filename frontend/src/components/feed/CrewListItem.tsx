import { Link } from 'react-router-dom';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  getLatestPostForCrew,
  getUser,
  relativeTime,
  type Crew,
} from '@/lib/mockData';

export default function CrewListItem({ crew }: { crew: Crew }) {
  const latest = getLatestPostForCrew(crew.id);
  const latestUser = latest ? getUser(latest.userId) : undefined;

  return (
    <Link
      to={`/crews/${crew.id}`}
      className="block border border-border bg-background hover:bg-accent/30 transition-colors p-6 group"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="label-mono text-muted-foreground">Crew</div>
          <h2 className="font-display text-2xl sm:text-3xl tracking-tight mt-1 group-hover:text-primary transition-colors">
            {crew.name}
          </h2>
        </div>
        <div className="shrink-0 flex -space-x-2">
          {crew.memberIds.slice(0, 4).map((id) => {
            const u = getUser(id);
            if (!u) return null;
            return (
              <Avatar key={id} className="ring-2 ring-background">
                <AvatarFallback>{u.initials}</AvatarFallback>
              </Avatar>
            );
          })}
          {crew.memberIds.length > 4 && (
            <span className="w-8 h-8 rounded-full bg-muted border border-border flex items-center justify-center label-mono text-muted-foreground ring-2 ring-background">
              +{crew.memberIds.length - 4}
            </span>
          )}
        </div>
      </div>

      <div className="hairline my-5" />

      <div className="flex items-baseline justify-between gap-4 label-mono text-muted-foreground">
        <span>{crew.memberIds.length} members</span>
        {latest && latestUser && (
          <span>
            <span className="text-foreground">{latestUser.displayName}</span>{' '}
            posted · {relativeTime(latest.postedAt)}
          </span>
        )}
      </div>
    </Link>
  );
}
