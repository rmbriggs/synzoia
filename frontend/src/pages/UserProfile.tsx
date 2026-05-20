import { useParams } from 'react-router-dom';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import SleepPost from '@/components/feed/SleepPost';
import {
  getStreakForUser,
  getUser,
  listPostsForUser,
} from '@/lib/mockData';

export default function UserProfile() {
  const { id } = useParams<{ id: string }>();
  const user = id ? getUser(id) : undefined;

  if (!user) {
    return (
      <>
        <PageHeader
          title="User not found"
          description="This user doesn't exist in the mock data layer."
        />
        <Card className="mt-6">
          <EmptyState message="Try /users/u-micah or /users/u-soren." />
        </Card>
      </>
    );
  }

  const streak = getStreakForUser(user.id);
  const recent = listPostsForUser(user.id, 5);

  return (
    <>
      <div className="flex items-center gap-4">
        <Avatar className="w-14 h-14">
          <AvatarFallback>{user.initials}</AvatarFallback>
        </Avatar>
        <div>
          <h1 className="font-display text-3xl tracking-tight">
            {user.displayName}
          </h1>
          <p className="label-mono text-muted-foreground mt-1">
            {user.timezone}
          </p>
        </div>
      </div>

      <Card className="mt-6">
        <div className="label-mono text-muted-foreground">Streaks</div>
        <div className="mt-3 grid grid-cols-2 gap-6">
          <div>
            <div className="font-display italic text-5xl text-primary tabular-nums">
              {streak.current}
            </div>
            <div className="label-mono text-muted-foreground mt-1">
              current · nights
            </div>
          </div>
          <div>
            <div className="font-display italic text-5xl tabular-nums">
              {streak.longest}
            </div>
            <div className="label-mono text-muted-foreground mt-1">
              longest · nights
            </div>
          </div>
        </div>
      </Card>

      <Card className="mt-4">
        <div className="label-mono text-muted-foreground mb-4">
          Recent posts
        </div>
        {recent.length === 0 ? (
          <EmptyState message="No posts yet." />
        ) : (
          <div>
            {recent.map((p) => (
              <SleepPost key={p.id} post={p} />
            ))}
          </div>
        )}
      </Card>
    </>
  );
}
