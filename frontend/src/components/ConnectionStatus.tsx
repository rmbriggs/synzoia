import { useQuery } from '@tanstack/react-query';
import { getDbHealth } from '@/api/health';

type Tone = 'ok' | 'warn' | 'err';

function tone(state: Tone): string {
  if (state === 'ok') return 'text-primary';
  if (state === 'warn') return 'text-amber-500';
  return 'text-destructive';
}

export default function ConnectionStatus() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health', 'db'],
    queryFn: getDbHealth,
    staleTime: 60_000,
  });

  let state: Tone = 'ok';
  let label = 'checking…';

  if (isLoading) {
    state = 'warn';
    label = 'checking…';
  } else if (isError || !data) {
    state = 'err';
    label = 'api unreachable';
  } else {
    const total = Object.values(data.tables);
    const present = total.filter((v) => v !== null).length;
    const rows = total.reduce((s: number, v) => s + (v ?? 0), 0);
    if (data.ok) {
      state = 'ok';
      label = `connected · ${present}/${total.length} tables · ${rows} rows`;
    } else {
      state = 'warn';
      label = `migration pending · ${present}/${total.length} tables`;
    }
  }

  return (
    <div className="inline-flex items-center gap-2 label-mono text-muted-foreground">
      <span
        className={`inline-block w-1.5 h-1.5 rounded-full ${tone(state)}`}
        style={{ background: 'currentColor' }}
        aria-hidden="true"
      />
      <span>DB · {label}</span>
    </div>
  );
}
