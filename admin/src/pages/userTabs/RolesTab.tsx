import { useEffect, useMemo, useState } from 'react';
import { api, extractErrorMessage } from '../../api/client';
import Table, { Column } from '../../components/Table';
import Button from '../../components/Button';
import Modal from '../../components/Modal';
import Input from '../../components/Input';
import Banner from '../../components/Banner';
import type { AdminRole } from '../../types';
import { PERMISSION_GROUPS, isSuperAdmin } from '../../constants/permissions';

interface FormState {
  name: string;
  permissions: string[];
}

const emptyForm: FormState = { name: '', permissions: [] };

function togglePerm(list: string[], perm: string): string[] {
  return list.includes(perm) ? list.filter((p) => p !== perm) : [...list, perm];
}

function addPerm(list: string[], perm: string): string[] {
  return list.includes(perm) ? list : [...list, perm];
}

function removePerm(list: string[], perm: string): string[] {
  return list.filter((p) => p !== perm);
}

export default function RolesTab() {
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<AdminRole | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<AdminRole[]>('/admin/roles');
      setRoles(data);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load roles') });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const superRoles = useMemo(() => roles.filter((r) => isSuperAdmin(r.permissions)), [roles]);
  const isLastSuper = (r: AdminRole) => isSuperAdmin(r.permissions) && superRoles.length === 1;

  // When editing, is this the last super-admin role?
  const editingIsLastSuper =
    !!editing && isSuperAdmin(editing.permissions) && superRoles.length === 1;
  const editFormIsStillSuper = isSuperAdmin(form.permissions);
  const editWouldBreakLastSuper = editingIsLastSuper && !editFormIsStillSuper;

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (r: AdminRole) => {
    setEditing(r);
    setForm({ name: r.name, permissions: [...r.permissions] });
    setModalOpen(true);
  };

  const togglePermission = (perm: string) => {
    const [group, action] = perm.split('.');
    setForm((f) => {
      const has = f.permissions.includes(perm);
      let next = f.permissions;

      // Find the group to see if it's granular.
      const g = PERMISSION_GROUPS.find((x) => x.key === group);
      if (!g) return f;

      if (!g.granular) {
        next = togglePerm(next, perm);
        return { ...f, permissions: next };
      }

      // Granular cascade rules:
      if (!has) {
        // Turning ON
        next = addPerm(next, perm);
        if (action !== 'view') {
          next = addPerm(next, `${group}.view`);
        }
      } else {
        // Turning OFF
        next = removePerm(next, perm);
        if (action === 'view') {
          // Clear add/edit/delete in the same group.
          for (const a of ['add', 'edit', 'delete']) {
            next = removePerm(next, `${group}.${a}`);
          }
        }
      }
      return { ...f, permissions: next };
    });
  };

  const save = async () => {
    if (editWouldBreakLastSuper) return;
    try {
      if (editing) {
        await api.put(`/admin/roles/${editing.id}`, form);
        setBanner({ kind: 'success', message: 'Role updated' });
      } else {
        await api.post('/admin/roles', form);
        setBanner({ kind: 'success', message: 'Role created' });
      }
      setModalOpen(false);
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Save failed') });
    }
  };

  const remove = async (r: AdminRole) => {
    if (isLastSuper(r)) return;
    if (!confirm(`Delete role "${r.name}"?`)) return;
    try {
      await api.delete(`/admin/roles/${r.id}`);
      setBanner({ kind: 'success', message: 'Role deleted' });
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Delete failed') });
    }
  };

  const columns: Column<AdminRole>[] = [
    { key: 'id', label: 'ID', className: 'w-16' },
    {
      key: 'name',
      label: 'Name',
      render: (r) => (
        <div className="flex items-center gap-2">
          <span>{r.name}</span>
          {isSuperAdmin(r.permissions) && (
            <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
              Super
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'permissions',
      label: 'Permissions',
      render: (r) => (
        <div className="flex flex-wrap gap-1">
          {r.permissions.length === 0 ? (
            <span className="text-xs text-textSecondary">None</span>
          ) : (
            r.permissions.map((p) => (
              <span key={p} className="rounded bg-primary/10 px-2 py-0.5 text-xs text-primary">
                {p}
              </span>
            ))
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      className: 'w-60',
      render: (r) => {
        const last = isLastSuper(r);
        return (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => openEdit(r)}>
              Edit
            </Button>
            <span title={last ? 'Last super-admin role — cannot delete.' : undefined}>
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
        <Button onClick={openCreate}>Add role</Button>
      </div>

      {banner && <Banner kind={banner.kind} message={banner.message} onClose={() => setBanner(null)} />}

      {loading ? (
        <div className="py-10 text-center text-sm text-textSecondary">Loading…</div>
      ) : (
        <Table columns={columns} rows={roles} />
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit ${editing.name}` : 'Add Role'}
        wide
        footer={
          <>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={save} disabled={editWouldBreakLastSuper}>
              {editing ? 'Save' : 'Create'}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          {editWouldBreakLastSuper && (
            <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
              This is the last super-admin role. You cannot remove any of its permissions.
              Restore all permissions to save, or create another super-admin role first.
            </div>
          )}

          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />

          <div>
            <div className="mb-2 text-xs font-medium text-textSecondary">Permissions</div>
            <div className="flex flex-col gap-2">
              {PERMISSION_GROUPS.map((g) => {
                if (!g.granular) {
                  const perm = `${g.key}.${g.actions[0]}`;
                  const checked = form.permissions.includes(perm);
                  return (
                    <label
                      key={g.key}
                      className="flex items-center gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm text-textPrimary"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => togglePermission(perm)}
                      />
                      <span className="font-medium">{g.label}</span>
                      <span className="text-xs text-textSecondary">({perm})</span>
                    </label>
                  );
                }
                return (
                  <div
                    key={g.key}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm text-textPrimary"
                  >
                    <span className="font-medium">{g.label}</span>
                    <div className="flex flex-wrap gap-3">
                      {g.actions.map((a) => {
                        const perm = `${g.key}.${a}`;
                        const checked = form.permissions.includes(perm);
                        return (
                          <label key={a} className="flex items-center gap-1.5 text-xs">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => togglePermission(perm)}
                            />
                            {a}
                          </label>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
