import { useEffect, useState } from 'react';
import { api, extractErrorMessage } from '../../api/client';
import Button from '../../components/Button';
import Input from '../../components/Input';
import Select from '../../components/Select';
import Banner from '../../components/Banner';

type Period = 'daily' | 'weekly' | 'monthly' | 'yearly' | 'from_start' | 'custom';

interface RegistrationsResponse {
  count: number;
}
interface ActiveUsersResponse {
  count: number;
}
interface EngagementResponse {
  avg_session_minutes?: number;
  total_sessions?: number;
  avg_messages_per_user?: number;
  breakdown?: Record<string, number | string>;
}
interface LanguageAnalyticsRow {
  language_id: number;
  language_name: string;
  learner_count: number;
}

function periodDates(p: Period): { from?: string; to?: string } {
  const now = new Date();
  const to = now.toISOString();
  const from = new Date(now);
  switch (p) {
    case 'daily':
      from.setDate(now.getDate() - 1);
      break;
    case 'weekly':
      from.setDate(now.getDate() - 7);
      break;
    case 'monthly':
      from.setMonth(now.getMonth() - 1);
      break;
    case 'yearly':
      from.setFullYear(now.getFullYear() - 1);
      break;
    case 'from_start':
      return {};
    case 'custom':
      return {};
  }
  return { from: from.toISOString(), to };
}

interface PeriodPickerState {
  period: Period;
  customFrom: string;
  customTo: string;
}

function PeriodPicker({
  state,
  setState,
}: {
  state: PeriodPickerState;
  setState: (s: PeriodPickerState) => void;
}) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="w-40">
        <Select
          label="Period"
          value={state.period}
          onChange={(e) => setState({ ...state, period: e.target.value as Period })}
        >
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="yearly">Yearly</option>
          <option value="from_start">From start</option>
          <option value="custom">Custom</option>
        </Select>
      </div>
      {state.period === 'custom' && (
        <>
          <Input
            label="From"
            type="date"
            value={state.customFrom}
            onChange={(e) => setState({ ...state, customFrom: e.target.value })}
          />
          <Input
            label="To"
            type="date"
            value={state.customTo}
            onChange={(e) => setState({ ...state, customTo: e.target.value })}
          />
        </>
      )}
    </div>
  );
}

function resolveParams(s: PeriodPickerState): Record<string, string> {
  if (s.period === 'custom') {
    const params: Record<string, string> = {};
    if (s.customFrom) params.from_date = new Date(s.customFrom).toISOString();
    if (s.customTo) params.to_date = new Date(s.customTo).toISOString();
    return params;
  }
  const { from, to } = periodDates(s.period);
  const params: Record<string, string> = {};
  if (from) params.from_date = from;
  if (to) params.to_date = to;
  return params;
}

export default function ReportsTab() {
  const [banner, setBanner] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  const [regState, setRegState] = useState<PeriodPickerState>({
    period: 'monthly',
    customFrom: '',
    customTo: '',
  });
  const [regCount, setRegCount] = useState<number | null>(null);
  const [regLoading, setRegLoading] = useState(false);

  const [actState, setActState] = useState<PeriodPickerState>({
    period: 'monthly',
    customFrom: '',
    customTo: '',
  });
  const [actCount, setActCount] = useState<number | null>(null);
  const [actLoading, setActLoading] = useState(false);

  const [engagement, setEngagement] = useState<EngagementResponse | null>(null);
  const [engLoading, setEngLoading] = useState(false);

  const [languageRows, setLanguageRows] = useState<LanguageAnalyticsRow[]>([]);
  const [langLoading, setLangLoading] = useState(false);

  const loadRegistrations = async () => {
    setRegLoading(true);
    try {
      const { data } = await api.get<RegistrationsResponse | number>(
        '/admin/reports/registrations',
        { params: resolveParams(regState) },
      );
      setRegCount(typeof data === 'number' ? data : (data.count ?? 0));
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load') });
    } finally {
      setRegLoading(false);
    }
  };

  const loadActiveUsers = async () => {
    setActLoading(true);
    try {
      const { data } = await api.get<ActiveUsersResponse | number>(
        '/admin/reports/active-users',
        { params: resolveParams(actState) },
      );
      setActCount(typeof data === 'number' ? data : (data.count ?? 0));
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load') });
    } finally {
      setActLoading(false);
    }
  };

  const loadEngagement = async () => {
    setEngLoading(true);
    try {
      const { data } = await api.get<EngagementResponse>('/admin/reports/engagement');
      setEngagement(data);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load') });
    } finally {
      setEngLoading(false);
    }
  };

  const loadLanguage = async () => {
    setLangLoading(true);
    try {
      const { data } = await api.get<LanguageAnalyticsRow[]>(
        '/admin/reports/language-analytics',
      );
      setLanguageRows(
        [...data].sort((a, b) => (b.learner_count ?? 0) - (a.learner_count ?? 0)),
      );
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load') });
    } finally {
      setLangLoading(false);
    }
  };

  useEffect(() => {
    loadEngagement();
    loadLanguage();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      {banner && (
        <Banner kind={banner.kind} message={banner.message} onClose={() => setBanner(null)} />
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="New User Registrations">
          <PeriodPicker state={regState} setState={setRegState} />
          <div className="mt-4 flex items-end justify-between">
            <div>
              <div className="text-xs uppercase text-textSecondary">Count</div>
              <div className="text-3xl font-bold text-textPrimary">
                {regCount === null ? '—' : regCount}
              </div>
            </div>
            <Button onClick={loadRegistrations} disabled={regLoading}>
              {regLoading ? 'Loading…' : 'Refresh'}
            </Button>
          </div>
        </Card>

        <Card title="Active Users">
          <PeriodPicker state={actState} setState={setActState} />
          <div className="mt-4 flex items-end justify-between">
            <div>
              <div className="text-xs uppercase text-textSecondary">Count</div>
              <div className="text-3xl font-bold text-textPrimary">
                {actCount === null ? '—' : actCount}
              </div>
            </div>
            <Button onClick={loadActiveUsers} disabled={actLoading}>
              {actLoading ? 'Loading…' : 'Refresh'}
            </Button>
          </div>
        </Card>

        <Card title="Engagement">
          {engLoading ? (
            <div className="text-sm text-textSecondary">Loading…</div>
          ) : engagement ? (
            <dl className="flex flex-col gap-2 text-sm">
              {Object.entries(engagement).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="capitalize text-textSecondary">{k.replace(/_/g, ' ')}</dt>
                  <dd className="font-medium text-textPrimary">
                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <div className="text-sm text-textSecondary">No data</div>
          )}
          <div className="mt-4">
            <Button variant="secondary" onClick={loadEngagement}>
              Refresh
            </Button>
          </div>
        </Card>

        <Card title="Language Analytics">
          {langLoading ? (
            <div className="text-sm text-textSecondary">Loading…</div>
          ) : languageRows.length === 0 ? (
            <div className="text-sm text-textSecondary">No data</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-textSecondary">
                  <th className="py-1">Language</th>
                  <th className="py-1 text-right">Learners</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {languageRows.map((r) => (
                  <tr key={r.language_id}>
                    <td className="py-1.5">{r.language_name}</td>
                    <td className="py-1.5 text-right font-medium">{r.learner_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="mt-4">
            <Button variant="secondary" onClick={loadLanguage}>
              Refresh
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-textSecondary">
        {title}
      </h3>
      {children}
    </div>
  );
}
