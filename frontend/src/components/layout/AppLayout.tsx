import { Link, NavLink, Outlet } from 'react-router-dom';

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex-1 py-3 text-center label-mono transition-colors ${
    isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
  }`;

const topNavClass = ({ isActive }: { isActive: boolean }) =>
  `label-mono transition-colors ${
    isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
  }`;

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="bg-background border-b border-border sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-baseline gap-2">
            <span
              data-logo-slot
              className="font-display italic text-xl tracking-tight text-foreground"
            >
              synzoia
            </span>
          </Link>
          <nav className="hidden sm:flex items-center gap-6">
            <NavLink to="/dashboard" className={topNavClass}>
              Today
            </NavLink>
            <NavLink to="/crews" className={topNavClass}>
              Crews
            </NavLink>
            <NavLink to="/settings" className={topNavClass}>
              Settings
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 sm:px-6 py-6 pb-24 sm:pb-6">
        <Outlet />
      </main>

      <nav
        className="sm:hidden fixed bottom-0 inset-x-0 bg-card border-t border-border"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="flex">
          <NavLink to="/dashboard" className={navLinkClass}>
            Today
          </NavLink>
          <NavLink to="/crews" className={navLinkClass}>
            Crews
          </NavLink>
          <NavLink to="/settings" className={navLinkClass}>
            Settings
          </NavLink>
        </div>
      </nav>
    </div>
  );
}

export default AppLayout;
