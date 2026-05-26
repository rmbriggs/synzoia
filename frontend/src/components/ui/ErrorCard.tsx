import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import { ApiError } from '@/api/client';

interface ErrorCardProps {
  error: unknown;
  onRetry: () => void;
  fallbackMessage?: string;
}

export default function ErrorCard({
  error,
  onRetry,
  fallbackMessage = 'Could not load this content.',
}: ErrorCardProps) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : fallbackMessage;
  return (
    <Card className="border-destructive/40 bg-destructive/5">
      <p className="text-destructive text-sm">{message}</p>
      <Button variant="secondary" className="mt-3" onClick={onRetry}>
        Try again
      </Button>
    </Card>
  );
}
