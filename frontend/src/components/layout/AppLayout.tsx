import { Link, NavLink, Outlet } from 'react-router-dom';

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="bg-background border-b border-border sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/crews" className="flex items-center gap-2">
            <span
              data-logo-slot
              className="text-lg font-semibold tracking-tight text-foreground"
            >
              synzoia
            </span>
          </Link>
          <Link
            to="/settings"
            className="hidden sm:inline text-sm text-muted-foreground hover:text-foreground"
          >
            Settings
          </Link>
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
          <NavLink
            to="/crews"
            className={({ isActive }) =>
              `flex-1 py-3 text-center text-sm font-medium ${
                isActive ? 'text-primary' : 'text-muted-foreground'
              }`
            }
          >
            Crews
          </NavLink>
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex-1 py-3 text-center text-sm font-medium ${
                isActive ? 'text-primary' : 'text-muted-foreground'
              }`
            }
          >
            Settings
          </NavLink>
        </div>
      </nav>
    </div>
  );
}

export default AppLayout;
