import { useQuery } from '@tanstack/react-query';
import { getDbDump, type Row } from '@/api/db';

const TABLE_ORDER = [
  'profiles',
  'groups',
  'memberships',
  'sleep_posts',
  'streaks',
] as const;

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return JSON.stringify(value);
}

function columnsOf(rows: Row[]): string[] {
  if (rows.length === 0) return [];
  return Object.keys(rows[0]);
}

function TableSection({
  name,
  index,
  rows,
  error,
}: {
  name: string;
  index: number;
  rows: Row[];
  error: string | null;
}) {
  const cols = columnsOf(rows);
  const indexLabel = String(index + 1).padStart(2, '0');

  return (
    <section>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <span className="font-display italic text-xl text-primary">
          {indexLabel}
        </span>
        <span className="font-display text-2xl tracking-tight">{name}</span>
        <span className="hairline flex-1 min-w-8" />
        <span className="label-mono text-muted-foreground">
          {error ? `error · ${error}` : `${rows.length} ${rows.length === 1 ? 'row' : 'rows'}`}
        </span>
      </div>

      {error ? (
        <div className="border border-destructive/40 bg-destructive/5 p-5 label-mono text-destructive">
          Could not read this table: {error}
        </div>
      ) : rows.length === 0 ? (
        <div className="border border-border bg-card/50 p-6 label-mono text-muted-foreground italic">
          (no rows yet)
        </div>
      ) : (
        <div className="border border-border overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                {cols.map((c) => (
                  <th
                    key={c}
                    className="label-mono text-muted-foreground text-left px-3 py-2 whitespace-nowrap"
                  >
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={i}
                  className="border-t border-border/60 hover:bg-accent/20 transition-colors"
                >
                  {cols.map((c) => (
                    <td
                      key={c}
                      className="px-3 py-2 font-mono whitespace-nowrap align-top"
                    >
                      {formatCell(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function DbExplorer() {
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['db', 'dump'],
    queryFn: getDbDump,
    staleTime: 10_000,
  });

  return (
    <div className="space-y-10">
      <div>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="hairline w-12" />
          <span className="label-mono text-muted-foreground">
            Section · Database
          </span>
        </div>
        <h1 className="mt-6 font-display text-4xl sm:text-5xl leading-[0.95] tracking-tight">
          Everything in <em className="text-primary">the backend.</em>
        </h1>
        <p className="mt-4 text-muted-foreground max-w-xl">
          Live read of every row in every v1 table. Capped at {data?.limit ?? 100} rows per
          table. Refresh to repull.
        </p>
        <div className="mt-6 flex items-center gap-4">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="label-mono text-muted-foreground border-b border-transparent hover:border-foreground hover:text-foreground transition-colors pb-0.5 disabled:opacity-50"
          >
            {isFetching ? 'refreshing…' : 'refresh →'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="label-mono text-muted-foreground">loading…</div>
      ) : isError || !data ? (
        <div className="border border-destructive/40 bg-destructive/5 p-5 label-mono text-destructive">
          Could not reach the API: {(error as Error)?.message ?? 'unknown error'}
        </div>
      ) : (
        <div className="space-y-12">
          {TABLE_ORDER.map((name, i) => (
            <TableSection
              key={name}
              name={name}
              index={i}
              rows={data.tables[name] ?? []}
              error={data.errors[name] ?? null}
            />
          ))}
        </div>
      )}
    </div>
  );
}
