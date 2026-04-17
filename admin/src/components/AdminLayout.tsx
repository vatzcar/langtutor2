import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuth } from '../hooks/useAuth';
import { canSeeRoute, MENU_VISIBILITY_PERMISSION } from '../constants/permissions';

export default function AdminLayout() {
  const { permissions } = useAuth();
  const location = useLocation();

  // Find the top-level route key ("/users", "/languages", etc).
  const path = '/' + (location.pathname.split('/')[1] ?? '');
  const requiresCheck = path in MENU_VISIBILITY_PERMISSION;
  const allowed = !requiresCheck || canSeeRoute(path, permissions);

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <main className="ml-64 min-h-screen flex-1 overflow-auto p-8">
        {allowed ? (
          <Outlet />
        ) : (
          <div className="flex min-h-[60vh] items-center justify-center">
            <div className="rounded-xl border border-slate-200 bg-white px-8 py-10 text-center shadow-sm">
              <h2 className="text-lg font-semibold text-textPrimary">Access denied</h2>
              <p className="mt-2 text-sm text-textSecondary">
                You don't have permission to view this page.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
