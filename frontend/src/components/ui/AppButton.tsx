import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router-dom';

type Variant = 'primary' | 'secondary' | 'ghost';

interface ButtonBaseProps {
  variant: Variant;
  disabled?: boolean;
  className?: string;
  children: ReactNode;
}

interface ButtonAsButtonProps extends ButtonBaseProps {
  to?: undefined;
  type?: ButtonHTMLAttributes<HTMLButtonElement>['type'];
  onClick?: ButtonHTMLAttributes<HTMLButtonElement>['onClick'];
}

interface ButtonAsLinkProps extends ButtonBaseProps {
  to: string;
}

type ButtonProps = ButtonAsButtonProps | ButtonAsLinkProps;

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: 'bg-indigo-600 hover:bg-indigo-700 text-white',
  secondary: 'bg-white border border-slate-200 hover:bg-slate-50 text-slate-900',
  ghost: 'text-slate-600 hover:text-slate-900',
};

const BASE = 'inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition';
const DISABLED = 'opacity-50 cursor-not-allowed';

function composeClasses(variant: Variant, disabled: boolean, className?: string) {
  const parts = [BASE, VARIANT_CLASSES[variant]];
  if (disabled) parts.push(DISABLED);
  if (className) parts.push(className);
  return parts.join(' ');
}

export default function Button(props: ButtonProps) {
  const { variant, disabled = false, className, children } = props;
  const composed = composeClasses(variant, disabled, className);

  if ('to' in props && props.to !== undefined) {
    if (disabled) {
      return <span className={composed} aria-disabled="true">{children}</span>;
    }
    return <Link to={props.to} className={composed}>{children}</Link>;
  }

  return (
    <button
      type={props.type ?? 'button'}
      onClick={props.onClick}
      disabled={disabled}
      className={composed}
    >
      {children}
    </button>
  );
}
