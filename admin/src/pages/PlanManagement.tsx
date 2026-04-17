import { useEffect, useState } from 'react';
import { api, extractErrorMessage } from '../api/client';
import Button from '../components/Button';
import Modal from '../components/Modal';
import Input from '../components/Input';
import Banner from '../components/Banner';
import type { Plan } from '../types';

interface PlanFormState {
  price_monthly: number;
  price_yearly: number;
  text_learning_limit_minutes: number;
  voice_call_limit_minutes: number;
  video_call_limit_minutes: number;
  agentic_voice_limit_monthly: number;
  coordinator_video_limit_monthly: number;
}

function planToForm(p: Plan): PlanFormState {
  return {
    price_monthly: p.price_monthly ?? 0,
    price_yearly: p.price_yearly ?? 0,
    text_learning_limit_minutes: p.text_learning_limit_minutes ?? 0,
    voice_call_limit_minutes: p.voice_call_limit_minutes ?? 0,
    video_call_limit_minutes: p.video_call_limit_minutes ?? 0,
    agentic_voice_limit_monthly: p.agentic_voice_limit_monthly ?? 0,
    coordinator_video_limit_monthly: p.coordinator_video_limit_monthly ?? 0,
  };
}

function formatLimit(value: number | null | undefined, unit: 'day' | 'month'): string {
  if (value == null) return '—';
  if (value === -1) return 'Not Available';
  if (value === 0) return 'Unlimited';
  return `${value} min / ${unit}`;
}

export default function PlanManagement() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);
  const [editing, setEditing] = useState<Plan | null>(null);
  const [form, setForm] = useState<PlanFormState | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Plan[]>('/admin/plans');
      setPlans(data);
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Failed to load plans') });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openEdit = (p: Plan) => {
    setEditing(p);
    setForm(planToForm(p));
  };

  const save = async () => {
    if (!editing || !form) return;
    let body: Partial<PlanFormState>;
    if (editing.slug === 'free') {
      // Free: only voice, video, and text limits are editable; no paid fields.
      body = {
        text_learning_limit_minutes: form.text_learning_limit_minutes,
        voice_call_limit_minutes: form.voice_call_limit_minutes,
        video_call_limit_minutes: form.video_call_limit_minutes,
      };
    } else {
      body = form;
    }
    try {
      await api.patch(`/admin/plans/${editing.id}`, body);
      setBanner({ kind: 'success', message: 'Plan updated' });
      setEditing(null);
      setForm(null);
      load();
    } catch (err) {
      setBanner({ kind: 'error', message: extractErrorMessage(err, 'Save failed') });
    }
  };

  const order: string[] = ['free', 'pro', 'ultra'];
  const sorted = [...plans].sort(
    (a, b) => order.indexOf(a.slug) - order.indexOf(b.slug),
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-textPrimary">Plan Management</h1>
        <p className="text-sm text-textSecondary">
          Configure the three subscription tiers.
          <span className="ml-1 font-medium">-1 = Not Available</span>,
          <span className="ml-1 font-medium">0 = Unlimited</span>,
          <span className="ml-1">positive = specific minute limit.</span>
        </p>
      </div>

      {banner && (
        <Banner kind={banner.kind} message={banner.message} onClose={() => setBanner(null)} />
      )}

      {loading ? (
        <div className="py-10 text-center text-sm text-textSecondary">Loading…</div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {sorted.map((p) => (
            <div
              key={p.id}
              className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-textPrimary capitalize">
                  {p.name || p.slug}
                </h2>
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary uppercase">
                  {p.slug}
                </span>
              </div>
              <div className="mt-3">
                <div className="text-2xl font-bold text-textPrimary">
                  ${(p.price_monthly ?? 0).toFixed(2)}
                  <span className="ml-1 text-sm font-normal text-textSecondary">/mo</span>
                </div>
                <div className="text-xs text-textSecondary">
                  ${(p.price_yearly ?? 0).toFixed(2)} yearly
                </div>
              </div>
              <dl className="mt-4 space-y-2 text-sm">
                <LimitRow label="Text learning" value={p.text_learning_limit_minutes} unit="day" />
                <LimitRow label="Voice call" value={p.voice_call_limit_minutes} unit="day" />
                <LimitRow label="Video call" value={p.video_call_limit_minutes} unit="day" />
                <LimitRow label="Agentic support" value={p.agentic_voice_limit_monthly} unit="month" />
                <LimitRow label="Coordinator support" value={p.coordinator_video_limit_monthly} unit="month" />
              </dl>
              <Button className="mt-6" onClick={() => openEdit(p)}>
                Edit
              </Button>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={editing !== null && form !== null}
        onClose={() => {
          setEditing(null);
          setForm(null);
        }}
        title={editing ? `Edit ${editing.name || editing.slug} plan` : ''}
        wide
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                setEditing(null);
                setForm(null);
              }}
            >
              Cancel
            </Button>
            <Button onClick={save}>Save</Button>
          </>
        }
      >
        {editing && form && (
          <div className="flex flex-col gap-4">
            <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-textSecondary">
              <strong>-1</strong> = Not Available · <strong>0</strong> = Unlimited · positive number = minutes
            </p>

            <div className="grid grid-cols-2 gap-4">
              {editing.slug !== 'free' && (
                <>
                  <Input
                    label="Price monthly ($)"
                    type="number"
                    step="0.01"
                    value={form.price_monthly}
                    onChange={(e) =>
                      setForm({ ...form, price_monthly: Number(e.target.value) })
                    }
                  />
                  <Input
                    label="Price yearly ($)"
                    type="number"
                    step="0.01"
                    value={form.price_yearly}
                    onChange={(e) =>
                      setForm({ ...form, price_yearly: Number(e.target.value) })
                    }
                  />
                </>
              )}

              <Input
                label="Text learning (min / day)"
                type="number"
                value={form.text_learning_limit_minutes}
                onChange={(e) =>
                  setForm({ ...form, text_learning_limit_minutes: Number(e.target.value) })
                }
              />
              <Input
                label="Voice call (min / day)"
                type="number"
                value={form.voice_call_limit_minutes}
                onChange={(e) =>
                  setForm({ ...form, voice_call_limit_minutes: Number(e.target.value) })
                }
              />
              <Input
                label="Video call (min / day)"
                type="number"
                value={form.video_call_limit_minutes}
                onChange={(e) =>
                  setForm({ ...form, video_call_limit_minutes: Number(e.target.value) })
                }
              />

              {editing.slug !== 'free' && (
                <>
                  <Input
                    label="Agentic support (min / month)"
                    type="number"
                    value={form.agentic_voice_limit_monthly}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        agentic_voice_limit_monthly: Number(e.target.value),
                      })
                    }
                  />
                  <Input
                    label="Coordinator support (min / month)"
                    type="number"
                    value={form.coordinator_video_limit_monthly}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        coordinator_video_limit_monthly: Number(e.target.value),
                      })
                    }
                  />
                </>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

function LimitRow({
  label,
  value,
  unit,
}: {
  label: string;
  value: number | null | undefined;
  unit: 'day' | 'month';
}) {
  const display = formatLimit(value, unit);
  const tone =
    value === -1
      ? 'text-slate-400'
      : value === 0
      ? 'text-success'
      : 'text-textPrimary';
  return (
    <div className="flex justify-between">
      <dt className="text-textSecondary">{label}</dt>
      <dd className={`font-medium ${tone}`}>{display}</dd>
    </div>
  );
}
