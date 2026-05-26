import Card from '@/components/ui/AppCard';

export default function FeedSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <div className="flex items-baseline gap-3">
            <span className="h-3 w-20 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 flex-1 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 w-12 bg-muted/60 rounded animate-pulse" />
          </div>
        </Card>
      ))}
    </div>
  );
}
