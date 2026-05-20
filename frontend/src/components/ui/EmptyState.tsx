type Props = {
  message?: string;
};

export function EmptyState({ message = 'Coming soon' }: Props) {
  return (
    <div className="py-12 text-center text-muted-foreground text-sm">
      {message}
    </div>
  );
}

export default EmptyState;
