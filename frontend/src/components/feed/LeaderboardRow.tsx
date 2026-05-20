import { Link } from 'react-router-dom';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  currentUserId,
  getUser,
  type LeaderboardEntry,
} from '@/lib/mockData';

export default function LeaderboardRow({ entry }: { entry: LeaderboardEntry }) {
  const user = getUser(entry.userId);
  if (!user) return null;
  const isMe = entry.userId === currentUserId;

  return (
    <li
      className={`grid grid-cols-[2.5rem_2.5rem_1fr_auto_auto] items-center gap-4 py-4 border-b border-border last:border-b-0 ${
        isMe ? 'bg-accent/30 -mx-4 px-4 rounded-md' : ''
      }`}
    >
      <span className="font-display italic text-2xl text-primary tabular-nums">
        {entry.rank}
      </span>

      <Link to={`/users/${user.id}`}>
        <Avatar>
          <AvatarFallback>{user.initials}</AvatarFallback>
        </Avatar>
      </Link>

      <div>
        <Link
          to={`/users/${user.id}`}
          className="font-display italic text-lg hover:text-primary transition-colors"
        >
          {user.displayName}
          {isMe && (
            <span className="label-mono text-muted-foreground ml-2">you</span>
          )}
        </Link>
      </div>

      <div className="text-right">
        <div className="font-mono text-base tabular-nums">
          {entry.hoursThisWeek}
          <span className="text-muted-foreground">h</span>
        </div>
        <div className="label-mono text-muted-foreground">this week</div>
      </div>

      <div className="text-right">
        <div className="font-mono text-base tabular-nums">
          {entry.streak}
        </div>
        <div className="label-mono text-muted-foreground">night streak</div>
      </div>
    </li>
  );
}
