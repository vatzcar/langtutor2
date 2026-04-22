import { useEffect, useRef, useState } from 'react';
import { api, assetUrl, extractErrorMessage } from '../api/client';
import Table, { Column } from '../components/Table';
import Button from '../components/Button';
import Modal from '../components/Modal';
import Input from '../components/Input';
import Select from '../components/Select';
import Banner from '../components/Banner';
import type { Language, Persona, PersonaType } from '../types';

interface FormState {
  name: string;
  language_id: string | '';
  gender: string;
  type: PersonaType;
  is_active: boolean;
}

const emptyForm: FormState = {
  name: '',
  language_id: '',
  gender: 'female',
  type: 'teacher',
  is_active: true,
};

export default function PersonaManagement() {
  const [languages, setLanguages] = useState<Language[]>([]);
  const [selectedLanguageId, setSelectedLanguageId] = useState<string | ''>('');
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Persona | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadTargetRef = useRef<string | null>(null);

  const loadLanguages = async () => {
    try {
      const { data } = await api.get<Language[]>('/admin/languages');
      setLanguages(data);
      if (data.length > 0 && selectedLanguageId === '') {
        setSelectedLanguageId(data[0].id);
      }
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load languages') });
    }
  };

  const loadPersonas = async () => {
    if (selectedLanguageId === '') {
      setPersonas([]);
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.get<Persona[]>('/admin/personas', {
        params: { language_id: selectedLanguageId },
      });
      setPersonas(data);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load personas') });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLanguages();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadPersonas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLanguageId]);

  const openCreate = () => {
    setEditing(null);
    setForm({
      ...emptyForm,
      language_id: selectedLanguageId === '' ? '' : selectedLanguageId,
    });
    setModalOpen(true);
  };

  const openEdit = (row: Persona) => {
    setEditing(row);
    setForm({
      name: row.name,
      language_id: row.language_id,
      gender: row.gender,
      type: row.type,
      is_active: row.is_active,
    });
    setModalOpen(true);
  };

  const save = async () => {
    if (form.language_id === '') {
      setBanner({ kind: 'error', message: 'Language is required' });
      return;
    }
    try {
      if (editing) {
        await api.patch(`/admin/personas/${editing.id}`, form);
        setBanner({ kind: 'success', message: 'Persona updated' });
      } else {
        const { is_active: _ignored, ...body } = form;
        void _ignored;
        await api.post('/admin/personas', body);
        setBanner({ kind: 'success', message: 'Persona created' });
      }
      setModalOpen(false);
      loadPersonas();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Save failed') });
    }
  };

  const remove = async (row: Persona) => {
    if (!confirm(`Delete persona "${row.name}"?`)) return;
    try {
      await api.delete(`/admin/personas/${row.id}`);
      setBanner({ kind: 'success', message: 'Persona deleted' });
      loadPersonas();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Delete failed') });
    }
  };

  const pickImage = (id: string) => {
    uploadTargetRef.current = id;
    fileInputRef.current?.click();
  };

  const uploadImage = async (file: File) => {
    const id = uploadTargetRef.current;
    if (!id) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      await api.post(`/admin/personas/${id}/image`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setBanner({ kind: 'success', message: 'Image uploaded' });
      loadPersonas();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Upload failed') });
    } finally {
      uploadTargetRef.current = null;
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const columns: Column<Persona>[] = [
    {
      key: 'image',
      label: 'Image',
      className: 'w-20',
      render: (r) =>
        r.image_url ? (
          <img src={assetUrl(r.image_url)} alt={r.name} className="h-10 w-10 rounded-full object-cover" />
        ) : (
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-xs text-textSecondary">
            —
          </div>
        ),
    },
    { key: 'name', label: 'Name' },
    { key: 'gender', label: 'Gender' },
    { key: 'type', label: 'Type' },
    {
      key: 'is_active',
      label: 'Active',
      render: (r) => (r.is_active ? 'Yes' : 'No'),
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
          <Button variant="secondary" onClick={() => pickImage(r.id)}>
            Upload image
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
          <h1 className="text-2xl font-semibold text-textPrimary">Personas</h1>
          <p className="text-sm text-textSecondary">
            Configure AI personas per language. Teaching style is chosen by each user during onboarding.
          </p>
        </div>
        <Button onClick={openCreate} disabled={selectedLanguageId === ''}>
          Add Persona
        </Button>
      </div>

      {banner && (
        <Banner kind={banner.kind} message={banner.message} onClose={() => setBanner(null)} />
      )}

      <div className="w-64">
        <Select
          label="Language"
          value={selectedLanguageId}
          onChange={(e) =>
            setSelectedLanguageId(e.target.value)
          }
        >
          <option value="">Select a language…</option>
          {languages.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name} ({l.locale})
            </option>
          ))}
        </Select>
      </div>

      {loading ? (
        <div className="py-10 text-center text-sm text-textSecondary">Loading…</div>
      ) : (
        <Table columns={columns} rows={personas} emptyMessage="No personas for this language" />
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) uploadImage(f);
        }}
      />

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit ${editing.name}` : 'Add Persona'}
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
          <Select
            label="Language"
            value={form.language_id}
            onChange={(e) =>
              setForm({ ...form, language_id: e.target.value })
            }
          >
            <option value="">Select…</option>
            {languages.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </Select>
          <Select
            label="Gender"
            value={form.gender}
            onChange={(e) => setForm({ ...form, gender: e.target.value })}
          >
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="nonbinary">Non-binary</option>
          </Select>
          <Select
            label="Type"
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value as PersonaType })}
          >
            <option value="teacher">Teacher</option>
            <option value="coordinator">Coordinator</option>
            <option value="peer">Peer</option>
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
