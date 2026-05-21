import { useId } from 'react';
import { cn } from '@/lib/utils';

type Props = {
  className?: string;
  /** Visual feel — "tide" is the high-arc curve from the screenshots,
   *  "wake" is a flatter, faster wave. Defaults to "tide". */
  shape?: 'tide' | 'wake';
};

/**
 * Decorative sine-curve mimicking the tide chart in the reference design.
 * Uses currentColor stops keyed to the primary token via a gradient ID so
 * multiple instances on a page do not collide.
 */
export default function WaveCurve({ className, shape = 'tide' }: Props) {
  const id = useId();
  const path =
    shape === 'tide'
      ? 'M0,72 C80,30 180,30 240,68 C300,106 380,108 400,72'
      : 'M0,68 C40,52 80,84 120,68 C160,52 200,84 240,68 C280,52 320,84 360,68 C380,60 400,72 400,72';

  return (
    <svg
      viewBox="0 0 400 110"
      preserveAspectRatio="none"
      aria-hidden="true"
      className={cn('w-full h-24 sm:h-28', className)}
    >
      <defs>
        <linearGradient id={`wave-fill-${id}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.28" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${path} L400,110 L0,110 Z`} fill={`url(#wave-fill-${id})`} />
      <path
        d={path}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
