import { apiFetch } from './client';

export interface DbHealth {
  ok: boolean;
  tables: Record<string, number | null>;
}

export function getDbHealth(): Promise<DbHealth> {
  return apiFetch<DbHealth>('/health/db');
}
