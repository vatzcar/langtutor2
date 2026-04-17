import { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  children: ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary: 'bg-primary text-white hover:bg-primary/90 disabled:bg-primary/50',
  secondary: 'bg-white text-textPrimary border border-slate-200 hover:bg-slate-50',
  danger: 'bg-error text-white hover:bg-error/90 disabled:bg-error/50',
  ghost: 'bg-transparent text-textPrimary hover:bg-slate-100',
};

export default function Button({
  variant = 'primary',
  className = '',
  children,
  ...rest
}: Props) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-70 ${variantClasses[variant]} ${className}`}
    >
      {children}
    </button>
  );
}
