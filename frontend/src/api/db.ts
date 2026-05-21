import { apiFetch } from './client';

export type Row = Record<string, unknown>;

export interface DbDump {
  tables: Record<string, Row[]>;
  errors: Record<string, string | null>;
  limit: number;
}

export function getDbDump(): Promise<DbDump> {
  return apiFetch<DbDump>('/db/dump');
}
