import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

// Deterministic, always-coastal gradient pairs (oklch). Kept on-palette so
// avatars never drift into non-coastal hues.
const COASTAL_GRADIENTS: [string, string][] = [
  ['oklch(0.61 0.11 185)', 'oklch(0.44 0.10 155)'], // teal -> fern
  ['oklch(0.44 0.10 155)', 'oklch(0.68 0.14 66)'],  // fern -> amber
  ['oklch(0.68 0.14 66)', 'oklch(0.41 0.09 42)'],   // amber -> bark
  ['oklch(0.61 0.11 185)', 'oklch(0.68 0.14 66)'],  // teal -> amber
  ['oklch(0.41 0.09 42)', 'oklch(0.44 0.10 155)'],  // bark -> fern
];

function hash(username: string): number {
  let h = 0;
  for (let i = 0; i < username.length; i++) h = (h * 31 + username.charCodeAt(i)) >>> 0;
  return h;
}

export function coastalGradientIndex(username: string): number {
  return hash(username) % COASTAL_GRADIENTS.length;
}

export function initials(username: string): string {
  const clean = username.replace(/[^a-zA-Z0-9]/g, '');
  return (clean.slice(0, 2) || '?').toUpperCase();
}

type Props = {
  username: string;
  size?: 'default' | 'sm' | 'lg';
  className?: string;
};

export function UserAvatar({ username, size = 'default', className }: Props) {
  const [from, to] = COASTAL_GRADIENTS[coastalGradientIndex(username)];
  return (
    <Avatar size={size} className={className}>
      <AvatarFallback
        className={cn('font-medium text-white')}
        style={{ backgroundImage: `linear-gradient(135deg, ${from}, ${to})` }}
      >
        {initials(username)}
      </AvatarFallback>
    </Avatar>
  );
}

export default UserAvatar;
