import { SelectHTMLAttributes, ReactNode } from 'react';

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  children: ReactNode;
}

export default function Select({ label, className = '', id, children, ...rest }: Props) {
  const selectId = id ?? rest.name;
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={selectId} className="text-xs font-medium text-textSecondary">
          {label}
        </label>
      )}
      <select
        id={selectId}
        {...rest}
        className={`rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-textPrimary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 ${className}`}
      >
        {children}
      </select>
    </div>
  );
}
