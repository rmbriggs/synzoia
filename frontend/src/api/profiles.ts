import { apiFetch } from './client';

export interface Profile {
  username: string;
  token: string;
  join_date: string;
}

export function createProfile(body: { username: string }): Promise<Profile> {
  return apiFetch<Profile>('/profiles', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
