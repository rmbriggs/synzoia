import type { ReactNode } from 'react';

interface CardProps {
  className?: string;
  children: ReactNode;
}

export default function Card({ className, children }: CardProps) {
  const base = 'bg-white border border-slate-200 rounded-2xl p-6';
  return <div className={className ? `${base} ${className}` : base}>{children}</div>;
}
