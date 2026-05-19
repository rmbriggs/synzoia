import { Link, NavLink, Outlet } from 'react-router-dom';

export default function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-background border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/crews" className="text-lg font-semibold tracking-tight">
            synzoia
          </Link>
          <Link
            to="/settings"
            className="hidden sm:inline text-sm text-slate-600 hover:text-slate-900"
          >
            Settings
          </Link>
        </div>
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto px-4 sm:px-6 py-6 pb-24 sm:pb-6">
        <Outlet />
      </main>

      <nav
        className="sm:hidden fixed bottom-0 inset-x-0 bg-white border-t border-slate-200 flex"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <NavLink
          to="/crews"
          className={({ isActive }) =>
            `flex-1 py-3 text-center text-sm font-medium ${
              isActive ? 'text-indigo-600' : 'text-slate-500'
            }`
          }
        >
          Crews
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `flex-1 py-3 text-center text-sm font-medium ${
              isActive ? 'text-indigo-600' : 'text-slate-500'
            }`
          }
        >
          Settings
        </NavLink>
      </nav>
    </div>
  );
}
