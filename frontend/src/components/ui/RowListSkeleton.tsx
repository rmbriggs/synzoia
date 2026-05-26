import Card from '@/components/ui/AppCard';

interface RowListSkeletonProps {
  rows?: number;
}

export default function RowListSkeleton({ rows = 6 }: RowListSkeletonProps) {
  return (
    <Card>
      <ul>
        {Array.from({ length: rows }).map((_, i) => (
          <li
            key={i}
            className="flex items-center gap-4 py-3 border-b border-border/60 last:border-b-0"
          >
            <span className="h-3 w-8 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 flex-1 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 w-16 bg-muted/60 rounded animate-pulse" />
          </li>
        ))}
      </ul>
    </Card>
  );
}
