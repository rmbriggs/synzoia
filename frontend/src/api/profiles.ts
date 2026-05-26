import { apiFetch } from './client';

export interface ProfileListEntry {
  username: string;
  join_date: string;
  total_steps_all_time: number;
}

export interface ProfileListResponse {
  profiles: ProfileListEntry[];
}

export function getProfiles(): Promise<ProfileListResponse> {
  return apiFetch<ProfileListResponse>('/profiles');
}

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
