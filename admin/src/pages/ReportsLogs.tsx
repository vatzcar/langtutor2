import { useState } from 'react';
import ReportsTab from './reportTabs/ReportsTab';
import LogsTab from './reportTabs/LogsTab';

type TabKey = 'reports' | 'logs';

export default function ReportsLogs() {
  const [active, setActive] = useState<TabKey>('reports');
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-textPrimary">Reports & Logs</h1>
        <p className="text-sm text-textSecondary">
          Review platform usage metrics and audit activity.
        </p>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        {(
          [
            { k: 'reports', l: 'Reports' },
            { k: 'logs', l: 'Logs' },
          ] as const
        ).map((t) => (
          <button
            key={t.k}
            onClick={() => setActive(t.k as TabKey)}
            className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              active === t.k
                ? 'border-primary text-primary'
                : 'border-transparent text-textSecondary hover:text-textPrimary'
            }`}
          >
            {t.l}
          </button>
        ))}
      </div>

      {active === 'reports' ? <ReportsTab /> : <LogsTab />}
    </div>
  );
}
