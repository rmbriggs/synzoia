interface EmptyStateProps {
  message?: string;
}

export default function EmptyState({ message = 'Coming soon' }: EmptyStateProps) {
  return (
    <div className="py-12 text-center text-slate-500 text-sm">{message}</div>
  );
}
