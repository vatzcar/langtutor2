import { useEffect, useRef, useState } from 'react';
import { api, assetUrl, extractErrorMessage } from '../api/client';
import Table, { Column } from '../components/Table';
import Button from '../components/Button';
import Modal from '../components/Modal';
import Input from '../components/Input';
import Banner from '../components/Banner';
import type { Language } from '../types';

interface FormState {
  name: string;
  locale: string;
  is_default: boolean;
  is_fallback: boolean;
  is_active: boolean;
}

const emptyForm: FormState = {
  name: '',
  locale: '',
  is_default: false,
  is_fallback: false,
  is_active: true,
};

export default function LanguageManagement() {
  const [items, setItems] = useState<Language[]>([]);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Language | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadTargetRef = useRef<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Language[]>('/admin/languages');
      setItems(data);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load languages') });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (row: Language) => {
    setEditing(row);
    setForm({
      name: row.name,
      locale: row.locale,
      is_default: row.is_default,
      is_fallback: row.is_fallback,
      is_active: row.is_active,
    });
    setModalOpen(true);
  };

  const save = async () => {
    try {
      if (editing) {
        await api.patch(`/admin/languages/${editing.id}`, form);
        setBanner({ kind: 'success', message: 'Language updated' });
      } else {
        const { is_active: _ignored, ...body } = form;
        void _ignored;
        await api.post('/admin/languages', body);
        setBanner({ kind: 'success', message: 'Language created' });
      }
      setModalOpen(false);
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Save failed') });
    }
  };

  const remove = async (row: Language) => {
    if (!confirm(`Delete language "${row.name}"?`)) return;
    try {
      await api.delete(`/admin/languages/${row.id}`);
      setBanner({ kind: 'success', message: 'Language deleted' });
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Delete failed') });
    }
  };

  const pickIcon = (id: string) => {
    uploadTargetRef.current = id;
    fileInputRef.current?.click();
  };

  const uploadIcon = async (file: File) => {
    const id = uploadTargetRef.current;
    if (!id) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      await api.post(`/admin/languages/${id}/icon`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setBanner({ kind: 'success', message: 'Icon uploaded' });
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Upload failed') });
    } finally {
      uploadTargetRef.current = null;
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const columns: Column<Language>[] = [
    { key: 'id', label: 'ID', className: 'w-16' },
    {
      key: 'icon',
      label: 'Icon',
      className: 'w-20',
      render: (r) =>
        r.icon_url ? (
          <img src={assetUrl(r.icon_url)} alt={r.name} className="h-8 w-8 rounded object-cover" />
        ) : (
          <span className="text-xs text-textSecondary">—</span>
        ),
    },
    { key: 'name', label: 'Name' },
    { key: 'locale', label: 'Locale' },
    {
      key: 'flags',
      label: 'Flags',
      render: (r) => (
        <div className="flex gap-1 text-xs">
          {r.is_default && (
            <span className="rounded bg-primary/10 px-2 py-0.5 text-primary">default</span>
          )}
          {r.is_fallback && (
            <span className="rounded bg-accent/20 px-2 py-0.5 text-amber-700">fallback</span>
          )}
          {!r.is_active && (
            <span className="rounded bg-error/10 px-2 py-0.5 text-error">inactive</span>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      className: 'w-80',
      render: (r) => (
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => openEdit(r)}>
            Edit
          </Button>
          <Button variant="secondary" onClick={() => pickIcon(r.id)}>
            Upload icon
          </Button>
          <Button variant="danger" onClick={() => remove(r)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-textPrimary">Languages</h1>
          <p className="text-sm text-textSecondary">
            Manage supported languages, locale codes, and icon assets.
          </p>
        </div>
        <Button onClick={openCreate}>Add Language</Button>
      </div>

      {banner && (
        <Banner kind={banner.kind} message={banner.message} onClose={() => setBanner(null)} />
      )}

      {loading ? (
        <div className="py-10 text-center text-sm text-textSecondary">Loading…</div>
      ) : (
        <Table columns={columns} rows={items} />
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) uploadIcon(f);
        }}
      />

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit ${editing.name}` : 'Add Language'}
        footer={
          <>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={save}>{editing ? 'Save' : 'Create'}</Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Input
            label="Locale (e.g. en-US)"
            value={form.locale}
            onChange={(e) => setForm({ ...form, locale: e.target.value })}
          />
          <label className="flex items-center gap-2 text-sm text-textPrimary">
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
            />
            Is default
          </label>
          <label className="flex items-center gap-2 text-sm text-textPrimary">
            <input
              type="checkbox"
              checked={form.is_fallback}
              onChange={(e) => setForm({ ...form, is_fallback: e.target.checked })}
            />
            Is fallback
          </label>
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
