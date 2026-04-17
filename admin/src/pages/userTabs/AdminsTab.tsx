import { useEffect, useMemo, useState } from 'react';
import { api, extractErrorMessage } from '../../api/client';
import Table, { Column } from '../../components/Table';
import Button from '../../components/Button';
import Modal from '../../components/Modal';
import Input from '../../components/Input';
import Select from '../../components/Select';
import Banner from '../../components/Banner';
import type { AdminRole, AdminUser } from '../../types';
import { isSuperAdmin } from '../../constants/permissions';

interface FormState {
  email: string;
  name: string;
  password: string;
  role_id: string | '';
  is_active: boolean;
}

const emptyForm: FormState = {
  email: '',
  name: '',
  password: '',
  role_id: '',
  is_active: true,
};

export default function AdminsTab() {
  const [admins, setAdmins] = useState<AdminUser[]>([]);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);

  const load = async () => {
    setLoading(true);
    try {
      const [{ data: a }, { data: r }] = await Promise.all([
        api.get<AdminUser[]>('/admin/admin-users'),
        api.get<AdminRole[]>('/admin/roles'),
      ]);
      setAdmins(a);
      setRoles(r);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load admins') });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Map roleId -> role for quick super-admin check.
  const rolesById = useMemo(() => {
    const m = new Map<string, AdminRole>();
    for (const r of roles) m.set(r.id, r);
    return m;
  }, [roles]);

  const isSuperAdminUser = (u: AdminUser): boolean => {
    const role = u.role ?? (u.role_id != null ? rolesById.get(u.role_id) : null);
    return !!role && isSuperAdmin(role.permissions);
  };

  const activeSuperAdmins = useMemo(
    () => admins.filter((a) => a.is_active && isSuperAdminUser(a)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [admins, rolesById],
  );

  const isLastActiveSuper = (u: AdminUser) =>
    activeSuperAdmins.length === 1 && activeSuperAdmins[0]?.id === u.id;

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (a: AdminUser) => {
    setEditing(a);
    setForm({
      email: a.email,
      name: a.name ?? '',
      password: '',
      role_id: a.role_id ?? '',
      is_active: a.is_active,
    });
    setModalOpen(true);
  };

  const save = async () => {
    try {
      if (editing) {
        const body: Record<string, unknown> = {
          name: form.name,
          role_id: form.role_id === '' ? null : form.role_id,
          is_active: form.is_active,
        };
        if (form.password) body.password = form.password;
        await api.patch(`/admin/admin-users/${editing.id}`, body);
        setBanner({ kind: 'success', message: 'Admin updated' });
      } else {
        await api.post('/admin/admin-users', {
          email: form.email,
          name: form.name,
          password: form.password,
          role_id: form.role_id === '' ? null : form.role_id,
        });
        setBanner({ kind: 'success', message: 'Admin created' });
      }
      setModalOpen(false);
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Save failed') });
    }
  };

  const remove = async (a: AdminUser) => {
    if (isLastActiveSuper(a)) return;
    if (!confirm(`Delete admin ${a.email}?`)) return;
    try {
      await api.delete(`/admin/admin-users/${a.id}`);
      setBanner({ kind: 'success', message: 'Admin deleted' });
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Delete failed') });
    }
  };

  const toggleActive = async (a: AdminUser) => {
    // Block deactivation of the last active super admin.
    if (a.is_active && isLastActiveSuper(a)) return;
    try {
      await api.patch(`/admin/admin-users/${a.id}`, { is_active: !a.is_active });
      setBanner({ kind: 'success', message: 'Status updated' });
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Action failed') });
    }
  };

  // When editing the last-active-super, don't let the user assign a non-super role.
  const editingIsLastActiveSuper = !!editing && isLastActiveSuper(editing);
  const selectedRoleIsSuper =
    form.role_id === ''
      ? false
      : !!rolesById.get(form.role_id) &&
        isSuperAdmin(rolesById.get(form.role_id)!.permissions);
  const editWouldDemoteLastSuper = editingIsLastActiveSuper && !selectedRoleIsSuper;
  const editWouldDeactivateLastSuper = editingIsLastActiveSuper && !form.is_active;
  const editBlocked = editWouldDemoteLastSuper || editWouldDeactivateLastSuper;

  const columns: Column<AdminUser>[] = [
    { key: 'id', label: 'ID', className: 'w-16' },
    { key: 'email', label: 'Email' },
    { key: 'name', label: 'Name', render: (r) => r.name ?? '—' },
    {
      key: 'role',
      label: 'Role',
      render: (r) => {
        const role = r.role ?? (r.role_id != null ? rolesById.get(r.role_id) : null);
        if (!role) return '—';
        return (
          <div className="flex items-center gap-1.5">
            <span>{role.name}</span>
            {isSuperAdmin(role.permissions) && (
              <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
                Super
              </span>
            )}
          </div>
        );
      },
    },
    {
      key: 'is_active',
      label: 'Active',
      render: (r) => (r.is_active ? 'Yes' : 'No'),
    },
    {
      key: 'created_at',
      label: 'Created',
      render: (r) => new Date(r.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      label: 'Actions',
      className: 'w-72',
      render: (r) => {
        const last = isLastActiveSuper(r);
        const tip = last ? 'Last active super-admin — protected.' : undefined;
        const disableDeactivate = last && r.is_active;
        return (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => openEdit(r)}>
              Edit
            </Button>
            <span title={disableDeactivate ? tip : undefined}>
              <Button
                variant="secondary"
                onClick={() => toggleActive(r)}
                disabled={disableDeactivate}
              >
                {r.is_active ? 'Deactivate' : 'Activate'}
              </Button>
            </span>
            <span title={last ? tip : undefined}>
              <Button variant="danger" onClick={() => remove(r)} disabled={last}>
                Delete
              </Button>
            </span>
          </div>
        );
      },
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={openCreate}>Add admin</Button>
      </div>

      {banner && <Banner kind={banner.kind} message={banner.message} onClose={() => setBanner(null)} />}

      {loading ? (
        <div className="py-10 text-center text-sm text-textSecondary">Loading…</div>
      ) : (
        <Table columns={columns} rows={admins} />
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit ${editing.email}` : 'Add Admin'}
        footer={
          <>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={save} disabled={editBlocked}>
              {editing ? 'Save' : 'Create'}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          {editBlocked && (
            <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
              This is the last active super-admin. You cannot demote their role or deactivate them.
            </div>
          )}

          <Input
            label="Email"
            type="email"
            value={form.email}
            disabled={!!editing}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Input
            label={editing ? 'New password (leave blank to keep)' : 'Password'}
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <Select
            label="Role"
            value={form.role_id}
            onChange={(e) =>
              setForm({ ...form, role_id: e.target.value })
            }
          >
            <option value="">—</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
                {isSuperAdmin(r.permissions) ? ' (super)' : ''}
              </option>
            ))}
          </Select>
          {editing && (
            <label className="flex items-center gap-2 text-sm text-textPrimary">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
              Active
            </label>
          )}
        </div>
      </Modal>
    </div>
  );
}
