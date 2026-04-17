import { useMemo, useState, useEffect } from 'react';
import EndUsersTab from './userTabs/EndUsersTab';
import AdminsTab from './userTabs/AdminsTab';
import RolesTab from './userTabs/RolesTab';
import { useAuth } from '../hooks/useAuth';

type TabKey = 'endUsers' | 'admins' | 'roles';

export default function UserManagement() {
  const { hasPermission } = useAuth();

  const tabs = useMemo(() => {
    const out: { key: TabKey; label: string }[] = [];
    if (hasPermission('users.view')) out.push({ key: 'endUsers', label: 'End Users' });
    if (hasPermission('admins.view')) {
      out.push({ key: 'admins', label: 'Admins' });
      out.push({ key: 'roles', label: 'Roles' });
    }
    return out;
  }, [hasPermission]);

  const [active, setActive] = useState<TabKey | null>(tabs[0]?.key ?? null);

  useEffect(() => {
    if (!active || !tabs.find((t) => t.key === active)) {
      setActive(tabs[0]?.key ?? null);
    }
  }, [tabs, active]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-textPrimary">User Management</h1>
        <p className="text-sm text-textSecondary">
          Manage end users, admin accounts, and the role/permission matrix. Use ban and
          subscription controls to enforce platform access.
        </p>
      </div>

      {tabs.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-textSecondary">
          You don't have permission to view any tabs here.
        </div>
      ) : (
        <>
          <div className="flex gap-2 border-b border-slate-200">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setActive(t.key)}
                className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                  active === t.key
                    ? 'border-primary text-primary'
                    : 'border-transparent text-textSecondary hover:text-textPrimary'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div>
            {active === 'endUsers' && <EndUsersTab />}
            {active === 'admins' && <AdminsTab />}
            {active === 'roles' && <RolesTab />}
          </div>
        </>
      )}
    </div>
  );
}
