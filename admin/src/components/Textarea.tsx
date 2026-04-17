import { TextareaHTMLAttributes } from 'react';

interface Props extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export default function Textarea({ label, className = '', id, ...rest }: Props) {
  const textareaId = id ?? rest.name;
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label htmlFor={textareaId} className="text-xs font-medium text-textSecondary">
          {label}
        </label>
      )}
      <textarea
        id={textareaId}
        {...rest}
        className={`rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-textPrimary outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 ${className}`}
      />
    </div>
  );
}
