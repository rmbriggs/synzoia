import type { ReactNode } from 'react';
import { Card as ShadcnCard, CardContent } from '@/components/ui/card';

type Props = {
  className?: string;
  children: ReactNode;
};

export function Card({ className, children }: Props) {
  return (
    <ShadcnCard className={className}>
      <CardContent className="p-6">{children}</CardContent>
    </ShadcnCard>
  );
}

export default Card;
