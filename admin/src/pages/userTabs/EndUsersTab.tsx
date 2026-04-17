import { useEffect, useState } from 'react';
import { api, extractErrorMessage } from '../../api/client';
import Table, { Column } from '../../components/Table';
import Button from '../../components/Button';
import Modal from '../../components/Modal';
import Input from '../../components/Input';
import Select from '../../components/Select';
import Banner from '../../components/Banner';
import type { Language, Plan, Subscription, User } from '../../types';

interface EditForm {
  name: string;
  native_language_id: string | '';
}

interface BanForm {
  reason: string;
  expires_at: string;
}

export default function EndUsersTab() {
  const [users, setUsers] = useState<User[]>([]);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

  const [editing, setEditing] = useState<User | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({ name: '', native_language_id: '' });

  const [banning, setBanning] = useState<User | null>(null);
  const [banForm, setBanForm] = useState<BanForm>({ reason: '', expires_at: '' });

  const [subFor, setSubFor] = useState<User | null>(null);
  const [subCurrent, setSubCurrent] = useState<Subscription | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subForm, setSubForm] = useState<{ plan_id: string | ''; expires_at: string }>({
    plan_id: '',
    expires_at: '',
  });

  const load = async () => {
    setLoading(true);
    try {
      const [{ data: u }, { data: l }] = await Promise.all([
        api.get<User[]>('/admin/users'),
        api.get<Language[]>('/admin/languages'),
      ]);
      setUsers(u);
      setLanguages(l);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load users') });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openEdit = (u: User) => {
    setEditing(u);
    setEditForm({
      name: u.name ?? '',
      native_language_id: u.native_language_id ?? '',
    });
  };

  const saveEdit = async () => {
    if (!editing) return;
    try {
      await api.patch(`/admin/users/${editing.id}`, {
        name: editForm.name,
        native_language_id:
          editForm.native_language_id === '' ? null : editForm.native_language_id,
      });
      setBanner({ kind: 'success', message: 'User updated' });
      setEditing(null);
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Save failed') });
    }
  };

  const toggleActive = async (u: User) => {
    try {
      await api.post(`/admin/users/${u.id}/toggle-active`);
      setBanner({ kind: 'success', message: 'Status updated' });
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Action failed') });
    }
  };

  const openBan = (u: User) => {
    setBanning(u);
    setBanForm({ reason: '', expires_at: '' });
  };

  const saveBan = async () => {
    if (!banning) return;
    try {
      await api.post(`/admin/users/${banning.id}/ban`, {
        reason: banForm.reason,
        expires_at: banForm.expires_at || null,
      });
      setBanner({ kind: 'success', message: 'User banned' });
      setBanning(null);
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Ban failed') });
    }
  };

  const unban = async (u: User) => {
    try {
      await api.post(`/admin/users/${u.id}/unban`);
      setBanner({ kind: 'success', message: 'User unbanned' });
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Unban failed') });
    }
  };

  const remove = async (u: User) => {
    if (!confirm(`Delete user ${u.email}? This is irreversible.`)) return;
    try {
      await api.delete(`/admin/users/${u.id}`);
      setBanner({ kind: 'success', message: 'User deleted' });
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Delete failed') });
    }
  };

  const openSubscription = async (u: User) => {
    setSubFor(u);
    setSubCurrent(null);
    setSubForm({ plan_id: '', expires_at: '' });
    try {
      const [{ data: sub }, { data: pl }] = await Promise.all([
        api.get<Subscription | null>(`/admin/subscriptions/user/${u.id}`),
        api.get<Plan[]>('/admin/plans'),
      ]);
      setSubCurrent(sub);
      setPlans(pl);
      if (sub) {
        setSubForm({
          plan_id: sub.plan_id,
          expires_at: sub.expires_at ? sub.expires_at.slice(0, 10) : '',
        });
      }
    } catch (err) {
      setBanner({
        kind: 'error',
        message: extractErrorMessage(err, 'Failed to load subscription'),
      });
    }
  };

  const assignSubscription = async () => {
    if (!subFor || subForm.plan_id === '') return;
    try {
      await api.post(`/admin/subscriptions/user/${subFor.id}/assign`, {
        plan_id: subForm.plan_id,
        expires_at: subForm.expires_at || null,
      });
      setBanner({ kind: 'success', message: 'Subscription assigned' });
      setSubFor(null);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Assign failed') });
    }
  };

  const updateSubscriptionExpiry = async () => {
    if (!subFor) return;
    try {
      await api.patch(`/admin/subscriptions/user/${subFor.id}/expiry`, {
        expires_at: subForm.expires_at || null,
      });
      setBanner({ kind: 'success', message: 'Expiry updated' });
      setSubFor(null);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Update failed') });
    }
  };

  const columns: Column<User>[] = [
    { key: 'id', label: 'ID', className: 'w-16' },
    { key: 'email', label: 'Email' },
    { key: 'name', label: 'Name', render: (r) => r.name ?? '—' },
    {
      key: 'status',
      label: 'Status',
      render: (r) => (
        <div className="flex flex-col gap-1">
          <span
            className={`inline-flex w-fit items-center rounded-full px-2 py-0.5 text-xs ${
              r.is_active
                ? 'bg-success/15 text-emerald-800'
                : 'bg-slate-200 text-slate-600'
            }`}
          >
            {r.is_active ? 'Active' : 'Inactive'}
          </span>
          {r.is_banned && (
            <span className="inline-flex w-fit items-center rounded-full bg-error/15 px-2 py-0.5 text-xs text-red-800">
              Banned
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'created_at',
      label: 'Created',
      render: (r) => new Date(r.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      label: 'Actions',
      className: 'w-[28rem]',
      render: (r) => (
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => openEdit(r)}>
            Edit
          </Button>
          <Button variant="secondary" onClick={() => toggleActive(r)}>
            {r.is_active ? 'Deactivate' : 'Activate'}
          </Button>
          {r.is_banned ? (
            <Button variant="secondary" onClick={() => unban(r)}>
              Unban
            </Button>
          ) : (
            <Button variant="secondary" onClick={() => openBan(r)}>
              Ban
            </Button>
          )}
          <Button variant="secondary" onClick={() => openSubscription(r)}>
            Subscription
          </Button>
          <Button variant="danger" onClick={() => remove(r)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      {banner && (
        <Banner kind={banner.kind} message={banner.message} onClose={() => setBanner(null)} />
      )}
      {loading ? (
        <div className="py-10 text-center text-sm text-textSecondary">Loading…</div>
      ) : (
        <Table columns={columns} rows={users} />
      )}

      <Modal
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={editing ? `Edit ${editing.email}` : ''}
        footer={
          <>
            <Button variant="ghost" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button onClick={saveEdit}>Save</Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="Name"
            value={editForm.name}
            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
          />
          <Select
            label="Native language"
            value={editForm.native_language_id}
            onChange={(e) =>
              setEditForm({
                ...editForm,
                native_language_id: e.target.value,
              })
            }
          >
            <option value="">—</option>
            {languages.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </Select>
        </div>
      </Modal>

      <Modal
        open={banning !== null}
        onClose={() => setBanning(null)}
        title={banning ? `Ban ${banning.email}` : ''}
        footer={
          <>
            <Button variant="ghost" onClick={() => setBanning(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={saveBan}>
              Ban
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="Reason"
            value={banForm.reason}
            onChange={(e) => setBanForm({ ...banForm, reason: e.target.value })}
          />
          <Input
            label="Expires at (leave blank for permanent)"
            type="datetime-local"
            value={banForm.expires_at}
            onChange={(e) => setBanForm({ ...banForm, expires_at: e.target.value })}
          />
        </div>
      </Modal>

      <Modal
        open={subFor !== null}
        onClose={() => setSubFor(null)}
        title={subFor ? `Subscription · ${subFor.email}` : ''}
        wide
        footer={
          <>
            <Button variant="ghost" onClick={() => setSubFor(null)}>
              Close
            </Button>
            {subCurrent && (
              <Button variant="secondary" onClick={updateSubscriptionExpiry}>
                Update expiry
              </Button>
            )}
            <Button onClick={assignSubscription}>
              {subCurrent ? 'Change plan' : 'Assign plan'}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            <div className="font-medium text-textPrimary">Current subscription</div>
            {subCurrent ? (
              <div className="mt-1 text-textSecondary">
                Plan: {subCurrent.plan?.name ?? `#${subCurrent.plan_id}`} ·{' '}
                {subCurrent.is_active ? 'active' : 'inactive'} · expires{' '}
                {subCurrent.expires_at
                  ? new Date(subCurrent.expires_at).toLocaleDateString()
                  : '—'}
              </div>
            ) : (
              <div className="mt-1 text-textSecondary">No active subscription</div>
            )}
          </div>
          <Select
            label="Plan"
            value={subForm.plan_id}
            onChange={(e) =>
              setSubForm({
                ...subForm,
                plan_id: e.target.value,
              })
            }
          >
            <option value="">Select a plan…</option>
            {plans.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name || p.slug}
              </option>
            ))}
          </Select>
          <Input
            label="Expires at"
            type="date"
            value={subForm.expires_at}
            onChange={(e) => setSubForm({ ...subForm, expires_at: e.target.value })}
          />
        </div>
      </Modal>
    </div>
  );
}
