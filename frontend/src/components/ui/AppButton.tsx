import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { Button as ShadcnButton } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type Variant = 'primary' | 'secondary' | 'ghost';

const variantMap = {
  primary: 'default',
  secondary: 'outline',
  ghost: 'ghost',
} as const;

type CommonProps = {
  variant?: Variant;
  className?: string;
  children: ReactNode;
  disabled?: boolean;
};

type ButtonAsButton = CommonProps & {
  to?: undefined;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
};

type ButtonAsLink = CommonProps & {
  to: string;
  onClick?: undefined;
  type?: undefined;
};

type Props = ButtonAsButton | ButtonAsLink;

export function Button(props: Props) {
  const { variant = 'primary', className, children, disabled } = props;
  const shadcnVariant = variantMap[variant];

  if ('to' in props && props.to) {
    if (disabled) {
      return (
        <ShadcnButton variant={shadcnVariant} disabled className={cn(className)}>
          {children}
        </ShadcnButton>
      );
    }
    return (
      <ShadcnButton asChild variant={shadcnVariant} className={cn(className)}>
        <Link to={props.to}>{children}</Link>
      </ShadcnButton>
    );
  }

  return (
    <ShadcnButton
      variant={shadcnVariant}
      disabled={disabled}
      onClick={props.onClick}
      type={props.type ?? 'button'}
      className={cn(className)}
    >
      {children}
    </ShadcnButton>
  );
}

export default Button;
