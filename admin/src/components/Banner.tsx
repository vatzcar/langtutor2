interface Props {
  kind: 'success' | 'error' | 'info';
  message: string;
  onClose?: () => void;
}

const styles: Record<Props['kind'], string> = {
  success: 'bg-success/15 text-emerald-800 border-success/30',
  error: 'bg-error/15 text-red-800 border-error/30',
  info: 'bg-primary/10 text-primary border-primary/30',
};

export default function Banner({ kind, message, onClose }: Props) {
  return (
    <div
      className={`flex items-start justify-between gap-4 rounded-lg border px-4 py-3 text-sm ${styles[kind]}`}
    >
      <span>{message}</span>
      {onClose && (
        <button onClick={onClose} className="text-xs uppercase tracking-wide opacity-75 hover:opacity-100">
          Dismiss
        </button>
      )}
    </div>
  );
}
