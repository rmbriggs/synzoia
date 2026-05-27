import { Link, NavLink, Outlet } from 'react-router-dom';
import { CircleUser, Database, Rss, Trophy, Users } from 'lucide-react';
import type { ReactNode } from 'react';
import ThemeToggle from '@/components/layout/ThemeToggle';
import { useCurrentUser } from '@/hooks/useCurrentUser';

const topNavClass = ({ isActive }: { isActive: boolean }) =>
  `label-mono transition-colors ${
    isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
  }`;

function BottomNavItem({
  to,
  icon,
  label,
  ariaLabel,
}: {
  to: string;
  icon: ReactNode;
  label: string;
  ariaLabel?: string;
}) {
  return (
    <NavLink
      to={to}
      end
      aria-label={ariaLabel}
      className={({ isActive }) =>
        `flex flex-col items-center justify-center gap-1 px-3 py-2 rounded-full transition-all ${
          isActive
            ? 'text-primary bg-[color-mix(in_oklch,var(--primary)_14%,transparent)]'
            : 'text-muted-foreground hover:text-foreground'
        }`
      }
    >
      <span aria-hidden="true">{icon}</span>
      <span className="text-[11px] font-medium tracking-wide">{label}</span>
    </NavLink>
  );
}

export function AppLayout() {
  const { currentUser } = useCurrentUser();
  const profileTarget = currentUser
    ? `/u/${encodeURIComponent(currentUser)}`
    : '/users';

  return (
    <div className="min-h-screen text-foreground">
      <header className="border-b border-border/60 sticky top-0 z-10 backdrop-blur-md bg-background/70">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/feed" className="flex items-baseline gap-2">
            <span
              data-logo-slot
              className="font-display italic text-xl tracking-tight text-foreground"
            >
              synzoia
            </span>
          </Link>
          <div className="flex items-center gap-6">
            <nav className="hidden sm:flex items-center gap-6">
              <NavLink to="/feed" className={topNavClass}>
                Feed
              </NavLink>
              <NavLink to="/leaderboard" className={topNavClass}>
                Leaderboard
              </NavLink>
              <NavLink to="/users" className={topNavClass}>
                Users
              </NavLink>
              <NavLink to="/db" className={topNavClass}>
                Database
              </NavLink>
            </nav>
            <Link
              to={profileTarget}
              aria-label="Your profile"
              title="Your profile"
              className="text-muted-foreground hover:text-foreground transition-colors p-2 -m-2"
            >
              <CircleUser size={20} strokeWidth={1.75} />
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 sm:px-6 py-6 pb-32 sm:pb-6">
        <Outlet />
      </main>

      <nav
        className="sm:hidden fixed bottom-4 inset-x-0 flex justify-center pointer-events-none z-20"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
        aria-label="Primary"
      >
        <div className="glass-bar flex items-center gap-1 p-1.5 pointer-events-auto">
          <BottomNavItem
            to="/feed"
            icon={<Rss size={18} strokeWidth={1.75} />}
            label="Feed"
          />
          <BottomNavItem
            to="/leaderboard"
            icon={<Trophy size={18} strokeWidth={1.75} />}
            label="Leaderboard"
          />
          <BottomNavItem
            to="/users"
            icon={<Users size={18} strokeWidth={1.75} />}
            label="Users"
          />
          <BottomNavItem
            to="/db"
            icon={<Database size={18} strokeWidth={1.75} />}
            label="Database"
          />
          <BottomNavItem
            to={profileTarget}
            icon={<CircleUser size={18} strokeWidth={1.75} />}
            label="Me"
            ariaLabel="Your profile"
          />
        </div>
      </nav>
    </div>
  );
}

export default AppLayout;
