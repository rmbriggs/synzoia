import { Moon, Trophy, Footprints, Dumbbell, type LucideIcon } from 'lucide-react';
import type { PostType } from '@/api/posts';

interface TypeMeta {
  icon: LucideIcon;
  label: string;
}

/**
 * Per-type icon + human label for feed posts. Only the icon shows; the
 * label is exposed to assistive tech via aria-label (see PostTypeIcon).
 * leaderboard_recap is intentionally absent — RecapPost is its own card.
 */
export const POST_TYPE_META: Partial<Record<PostType, TypeMeta>> = {
  sleep: { icon: Moon, label: 'Sleep' },
  steps_milestone: { icon: Trophy, label: 'Milestone' },
  steps: { icon: Footprints, label: 'Steps' },
  workout: { icon: Dumbbell, label: 'Workout' },
};

export function PostTypeIcon({ type }: { type: PostType }) {
  const meta = POST_TYPE_META[type];
  if (!meta) return null;
  const Icon = meta.icon;
  return (
    <Icon
      size={16}
      strokeWidth={1.75}
      role="img"
      aria-label={meta.label}
      className="text-muted-foreground shrink-0"
    />
  );
}
