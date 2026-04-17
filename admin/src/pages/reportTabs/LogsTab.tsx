import { useEffect, useState } from 'react';
import { api, extractErrorMessage } from '../../api/client';
import Table, { Column } from '../../components/Table';
import Input from '../../components/Input';
import Select from '../../components/Select';
import Button from '../../components/Button';
import Banner from '../../components/Banner';
import type { AuditLog } from '../../types';

interface Filters {
  action: string;
  actor_type: string;
  from_date: string;
  to_date: string;
  sort_by: 'created_at' | 'action';
  sort_order: 'asc' | 'desc';
}

const defaultFilters: Filters = {
  action: '',
  actor_type: '',
  from_date: '',
  to_date: '',
  sort_by: 'created_at',
  sort_order: 'desc',
};

const PAGE_SIZE = 50;

export default function LogsTab() {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [banner, setBanner] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  const buildParams = (skipVal: number): Record<string, string | number> => {
    const params: Record<string, string | number> = {
      skip: skipVal,
      limit: PAGE_SIZE,
      sort_by: filters.sort_by,
      sort_order: filters.sort_order,
    };
    if (filters.action) params.action = filters.action;
    if (filters.actor_type) params.actor_type = filters.actor_type;
    if (filters.from_date) params.from_date = new Date(filters.from_date).toISOString();
    if (filters.to_date) params.to_date = new Date(filters.to_date).toISOString();
    return params;
  };

  const load = async (reset: boolean) => {
    setLoading(true);
    try {
      const nextSkip = reset ? 0 : skip;
      const { data } = await api.get<AuditLog[]>('/admin/logs', { params: buildParams(nextSkip) });
      if (reset) {
        setLogs(data);
        setSkip(data.length);
      } else {
        setLogs((prev) => [...prev, ...data]);
        setSkip(nextSkip + data.length);
      }
      setHasMore(data.length === PAGE_SIZE);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load logs') });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyFilters = () => {
    setSkip(0);
    load(true);
  };

  const reset = () => {
    setFilters(defaultFilters);
    setTimeout(() => load(true), 0);
  };

  const columns: Column<AuditLog>[] = [
    { key: 'id', label: 'ID', className: 'w-16' },
    {
      key: 'created_at',
      label: 'When',
      render: (r) => new Date(r.created_at).toLocaleString(),
    },
    { key: 'actor_type', label: 'Actor type' },
    { key: 'actor_id', label: 'Actor', render: (r) => r.actor_id ?? '—' },
    { key: 'action', label: 'Action' },
    { key: 'resource_type', label: 'Resource', render: (r) => r.resource_type ?? '—' },
    { key: 'resource_id', label: 'Res ID', render: (r) => r.resource_id ?? '—' },
    { key: 'ip_address', label: 'IP', render: (r) => r.ip_address ?? '—' },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
          <Input
            label="Action"
            value={filters.action}
            onChange={(e) => setFilters({ ...filters, action: e.target.value })}
          />
          <Select
            label="Actor type"
            value={filters.actor_type}
            onChange={(e) => setFilters({ ...filters, actor_type: e.target.value })}
          >
            <option value="">Any</option>
            <option value="admin">admin</option>
            <option value="user">user</option>
            <option value="system">system</option>
          </Select>
          <Input
            label="From"
            type="date"
            value={filters.from_date}
            onChange={(e) => setFilters({ ...filters, from_date: e.target.value })}
          />
          <Input
            label="To"
            type="date"
            value={filters.to_date}
            onChange={(e) => setFilters({ ...filters, to_date: e.target.value })}
          />
          <Select
            label="Sort by"
            value={filters.sort_by}
            onChange={(e) =>
              setFilters({ ...filters, sort_by: e.target.value as Filters['sort_by'] })
            }
          >
            <option value="created_at">created_at</option>
            <option value="action">action</option>
          </Select>
          <Select
            label="Order"
            value={filters.sort_order}
            onChange={(e) =>
              setFilters({ ...filters, sort_order: e.target.value as Filters['sort_order'] })
            }
          >
            <option value="desc">desc</option>
            <option value="asc">asc</option>
          </Select>
        </div>
        <div className="mt-3 flex justify-end gap-2">
          <Button variant="ghost" onClick={reset}>
            Reset
          </Button>
          <Button onClick={applyFilters} disabled={loading}>
            Apply
          </Button>
        </div>
      </div>

      {banner && (
        <Banner kind={banner.kind} message={banner.message} onClose={() => setBanner(null)} />
      )}

      <Table columns={columns} rows={logs} emptyMessage="No audit log entries" />

      <div className="flex justify-center">
        <Button
          variant="secondary"
          onClick={() => load(false)}
          disabled={loading || !hasMore}
        >
          {loading ? 'Loading…' : hasMore ? 'Load more' : 'No more results'}
        </Button>
      </div>
    </div>
  );
}
