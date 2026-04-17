import { InputHTMLAttributes } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export default function Input({ label, error, className = '', id, ...rest }: Props) {
  const inputId = id ?? rest.name;
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={inputId} className="text-xs font-medium text-textSecondary">
          {label}
        </label>
      )}
      <input
        id={inputId}
        {...rest}
        className={`rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-textPrimary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 ${className}`}
      />
      {error && <span className="text-xs text-error">{error}</span>}
    </div>
  );
}
