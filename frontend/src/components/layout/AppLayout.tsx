import { Link, NavLink, Outlet } from 'react-router-dom';
import { Calendar, Settings as SettingsIcon, Users } from 'lucide-react';
import type { ReactNode } from 'react';
import ThemeToggle from '@/components/layout/ThemeToggle';

const topNavClass = ({ isActive }: { isActive: boolean }) =>
  `label-mono transition-colors ${
    isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
  }`;

function BottomNavItem({
  to,
  icon,
  label,
}: {
  to: string;
  icon: ReactNode;
  label: string;
}) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `flex flex-col items-center justify-center gap-1 px-5 py-2 rounded-full transition-all ${
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
  return (
    <div className="min-h-screen text-foreground">
      <header className="border-b border-border/60 sticky top-0 z-10 backdrop-blur-md bg-background/70">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-baseline gap-2">
            <span
              data-logo-slot
              className="font-display italic text-xl tracking-tight text-foreground"
            >
              synzoia
            </span>
          </Link>
          <div className="flex items-center gap-6">
            <nav className="hidden sm:flex items-center gap-6">
              <NavLink to="/dashboard" className={topNavClass}>
                Today
              </NavLink>
              <NavLink to="/crews" className={topNavClass}>
                Crews
              </NavLink>
              <NavLink to="/db" className={topNavClass}>
                Database
              </NavLink>
              <NavLink to="/settings" className={topNavClass}>
                Settings
              </NavLink>
            </nav>
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
            to="/dashboard"
            icon={<Calendar size={18} strokeWidth={1.75} />}
            label="Today"
          />
          <BottomNavItem
            to="/crews"
            icon={<Users size={18} strokeWidth={1.75} />}
            label="Crews"
          />
          <BottomNavItem
            to="/settings"
            icon={<SettingsIcon size={18} strokeWidth={1.75} />}
            label="Settings"
          />
        </div>
      </nav>
    </div>
  );
}

export default AppLayout;
