import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type Props = {
  className?: string;
  children: ReactNode;
};

export function Card({ className, children }: Props) {
  return (
    <div className={cn('surface-glass p-6', className)}>{children}</div>
  );
}

export default Card;
