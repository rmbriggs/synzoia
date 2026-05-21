/**
 * In-memory mock data layer. Replace each export with a React Query hook
 * once the backend ships.
 */

export type User = {
  id: string;
  displayName: string;
  initials: string;
  timezone: string;
};

export type SleepSource =
  | 'manual'
  | 'apple_health'
  | 'whoop'
  | 'oura'
  | 'fitbit'
  | 'garmin';

export type SleepPost = {
  id: string;
  userId: string;
  crewId: string;
  bedtime: string; // ISO
  wake: string; // ISO
  hours: number;
  quality: number; // 1-100
  note?: string;
  source: SleepSource;
  reactions: { emoji: string; count: number }[];
  postedAt: string; // ISO
};

export type LeaderboardEntry = {
  userId: string;
  hoursThisWeek: number;
  streak: number;
  rank: number;
};

export type ChatMessage = {
  id: string;
  userId: string;
  crewId: string;
  body: string;
  sentAt: string; // ISO
};

export type Crew = {
  id: string;
  name: string;
  memberIds: string[];
  createdAt: string;
};

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export const users: Record<string, User> = {
  'u-micah': {
    id: 'u-micah',
    displayName: 'Micah',
    initials: 'MB',
    timezone: 'America/Chicago',
  },
  'u-aria': {
    id: 'u-aria',
    displayName: 'Aria',
    initials: 'AR',
    timezone: 'America/Chicago',
  },
  'u-jay': {
    id: 'u-jay',
    displayName: 'Jay',
    initials: 'JL',
    timezone: 'America/New_York',
  },
  'u-soren': {
    id: 'u-soren',
    displayName: 'Soren',
    initials: 'SD',
    timezone: 'Europe/Lisbon',
  },
  'u-noor': {
    id: 'u-noor',
    displayName: 'Noor',
    initials: 'NK',
    timezone: 'America/Chicago',
  },
  'u-eli': {
    id: 'u-eli',
    displayName: 'Eli',
    initials: 'EW',
    timezone: 'America/Denver',
  },
};

export const currentUserId = 'u-micah';

export function getUser(id: string): User | undefined {
  return users[id];
}

export function getCurrentUser(): User {
  return users[currentUserId];
}

// ---------------------------------------------------------------------------
// Crews
// ---------------------------------------------------------------------------

export const crews: Record<string, Crew> = {
  'c-owls': {
    id: 'c-owls',
    name: 'The Night Owls',
    memberIds: ['u-micah', 'u-aria', 'u-jay', 'u-soren', 'u-noor'],
    createdAt: '2026-04-12T00:00:00Z',
  },
  'c-capstone': {
    id: 'c-capstone',
    name: 'Capstone Crew',
    memberIds: ['u-micah', 'u-eli', 'u-jay'],
    createdAt: '2026-02-08T00:00:00Z',
  },
};

export function listCrewsForUser(userId: string): Crew[] {
  return Object.values(crews).filter((c) => c.memberIds.includes(userId));
}

export function getCrew(id: string): Crew | undefined {
  return crews[id];
}

// ---------------------------------------------------------------------------
// Sleep posts
// ---------------------------------------------------------------------------

const now = Date.now();
const HOUR = 60 * 60 * 1000;
const DAY = 24 * HOUR;

function iso(offsetMs: number) {
  return new Date(now - offsetMs).toISOString();
}

export const sleepPosts: SleepPost[] = [
  // The Night Owls — most recent first
  {
    id: 'p-001',
    userId: 'u-aria',
    crewId: 'c-owls',
    bedtime: iso(11 * HOUR + 30 * 60 * 1000),
    wake: iso(2 * HOUR),
    hours: 8.5,
    quality: 88,
    note: 'first time in two weeks I slept past my alarm — the body knew',
    source: 'apple_health',
    reactions: [
      { emoji: '😴', count: 3 },
      { emoji: '🔥', count: 1 },
    ],
    postedAt: iso(2 * HOUR),
  },
  {
    id: 'p-002',
    userId: 'u-jay',
    crewId: 'c-owls',
    bedtime: iso(10 * HOUR),
    wake: iso(3 * HOUR),
    hours: 7,
    quality: 72,
    note: 'okay-ish. neighbor’s dog ruined the 5am stretch.',
    source: 'manual',
    reactions: [
      { emoji: '🐶', count: 2 },
      { emoji: '🫠', count: 1 },
    ],
    postedAt: iso(3 * HOUR),
  },
  {
    id: 'p-003',
    userId: 'u-soren',
    crewId: 'c-owls',
    bedtime: iso(13 * HOUR),
    wake: iso(5 * HOUR),
    hours: 8,
    quality: 91,
    note: 'lisbon morning, all is well',
    source: 'whoop',
    reactions: [{ emoji: '☀️', count: 4 }],
    postedAt: iso(5 * HOUR),
  },
  {
    id: 'p-004',
    userId: 'u-micah',
    crewId: 'c-owls',
    bedtime: iso(12 * HOUR + 15 * 60 * 1000),
    wake: iso(4 * HOUR + 15 * 60 * 1000),
    hours: 8,
    quality: 80,
    source: 'manual',
    reactions: [{ emoji: '👏', count: 2 }],
    postedAt: iso(4 * HOUR),
  },
  {
    id: 'p-005',
    userId: 'u-noor',
    crewId: 'c-owls',
    bedtime: iso(DAY + 11 * HOUR),
    wake: iso(DAY + 3 * HOUR),
    hours: 8,
    quality: 84,
    note: 'paper turned in. now I can rest.',
    source: 'manual',
    reactions: [
      { emoji: '🎉', count: 5 },
      { emoji: '📝', count: 2 },
    ],
    postedAt: iso(DAY + 3 * HOUR),
  },
  {
    id: 'p-006',
    userId: 'u-aria',
    crewId: 'c-owls',
    bedtime: iso(DAY + 12 * HOUR),
    wake: iso(DAY + 4 * HOUR),
    hours: 8,
    quality: 76,
    source: 'manual',
    reactions: [],
    postedAt: iso(DAY + 4 * HOUR),
  },
  {
    id: 'p-007',
    userId: 'u-jay',
    crewId: 'c-owls',
    bedtime: iso(2 * DAY + 9 * HOUR),
    wake: iso(2 * DAY + 3 * HOUR),
    hours: 6,
    quality: 55,
    note: 'rough one. travel day.',
    source: 'oura',
    reactions: [{ emoji: '🫂', count: 3 }],
    postedAt: iso(2 * DAY + 3 * HOUR),
  },
  {
    id: 'p-008',
    userId: 'u-micah',
    crewId: 'c-owls',
    bedtime: iso(2 * DAY + 11 * HOUR + 45 * 60 * 1000),
    wake: iso(2 * DAY + 3 * HOUR + 45 * 60 * 1000),
    hours: 8,
    quality: 82,
    source: 'manual',
    reactions: [{ emoji: '🌙', count: 1 }],
    postedAt: iso(2 * DAY + 3 * HOUR),
  },

  // Capstone Crew
  {
    id: 'p-101',
    userId: 'u-eli',
    crewId: 'c-capstone',
    bedtime: iso(10 * HOUR + 30 * 60 * 1000),
    wake: iso(3 * HOUR),
    hours: 7.5,
    quality: 79,
    note: 'demo prep wrapped at 11. small miracle.',
    source: 'manual',
    reactions: [
      { emoji: '🚀', count: 2 },
      { emoji: '🛠️', count: 1 },
    ],
    postedAt: iso(3 * HOUR),
  },
  {
    id: 'p-102',
    userId: 'u-micah',
    crewId: 'c-capstone',
    bedtime: iso(12 * HOUR + 15 * 60 * 1000),
    wake: iso(4 * HOUR + 15 * 60 * 1000),
    hours: 8,
    quality: 80,
    source: 'manual',
    reactions: [{ emoji: '👏', count: 1 }],
    postedAt: iso(4 * HOUR),
  },
];

const SOURCE_LABELS: Record<SleepSource, string> = {
  manual: 'manual',
  apple_health: 'Apple Health',
  whoop: 'Whoop',
  oura: 'Oura',
  fitbit: 'Fitbit',
  garmin: 'Garmin',
};

export function sourceLabel(source: SleepSource): string {
  return SOURCE_LABELS[source];
}

export function listPostsForCrew(crewId: string, limit?: number): SleepPost[] {
  const filtered = sleepPosts
    .filter((p) => p.crewId === crewId)
    .sort(
      (a, b) =>
        new Date(b.postedAt).getTime() - new Date(a.postedAt).getTime(),
    );
  return typeof limit === 'number' ? filtered.slice(0, limit) : filtered;
}

export function listPostsForUser(userId: string, limit = 5): SleepPost[] {
  return sleepPosts
    .filter((p) => p.userId === userId)
    .sort(
      (a, b) =>
        new Date(b.postedAt).getTime() - new Date(a.postedAt).getTime(),
    )
    .slice(0, limit);
}

export function getLatestPostForCrew(crewId: string): SleepPost | undefined {
  return listPostsForCrew(crewId, 1)[0];
}

// ---------------------------------------------------------------------------
// Leaderboard (computed from posts, hand-tuned for the demo)
// ---------------------------------------------------------------------------

const leaderboards: Record<string, LeaderboardEntry[]> = {
  'c-owls': [
    { userId: 'u-soren', hoursThisWeek: 56, streak: 24, rank: 1 },
    { userId: 'u-aria', hoursThisWeek: 53, streak: 12, rank: 2 },
    { userId: 'u-micah', hoursThisWeek: 52, streak: 18, rank: 3 },
    { userId: 'u-noor', hoursThisWeek: 51, streak: 6, rank: 4 },
    { userId: 'u-jay', hoursThisWeek: 44, streak: 3, rank: 5 },
  ],
  'c-capstone': [
    { userId: 'u-eli', hoursThisWeek: 51, streak: 9, rank: 1 },
    { userId: 'u-micah', hoursThisWeek: 50, streak: 18, rank: 2 },
    { userId: 'u-jay', hoursThisWeek: 44, streak: 3, rank: 3 },
  ],
};

export function getLeaderboardForCrew(crewId: string): LeaderboardEntry[] {
  return leaderboards[crewId] ?? [];
}

export function getStreakForUser(userId: string): {
  current: number;
  longest: number;
} {
  const fromOwls = leaderboards['c-owls']?.find((e) => e.userId === userId);
  const current = fromOwls?.streak ?? 0;
  return { current, longest: Math.max(current, 32) };
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export const chatMessages: ChatMessage[] = [
  {
    id: 'm-001',
    userId: 'u-soren',
    crewId: 'c-owls',
    body: 'lisbon morning. ☕️',
    sentAt: iso(4 * HOUR + 30 * 60 * 1000),
  },
  {
    id: 'm-002',
    userId: 'u-jay',
    crewId: 'c-owls',
    body: 'jealous',
    sentAt: iso(4 * HOUR + 25 * 60 * 1000),
  },
  {
    id: 'm-003',
    userId: 'u-aria',
    crewId: 'c-owls',
    body: 'soren is just here to ruin the leaderboard for the rest of us',
    sentAt: iso(4 * HOUR + 12 * 60 * 1000),
  },
  {
    id: 'm-004',
    userId: 'u-soren',
    crewId: 'c-owls',
    body: '24-night streak says hi',
    sentAt: iso(4 * HOUR + 10 * 60 * 1000),
  },
  {
    id: 'm-005',
    userId: 'u-micah',
    crewId: 'c-owls',
    body: 'i’ll catch you by friday',
    sentAt: iso(3 * HOUR + 50 * 60 * 1000),
  },
  {
    id: 'm-006',
    userId: 'u-noor',
    crewId: 'c-owls',
    body: 'going to bed in five. night, crew. 🌙',
    sentAt: iso(30 * 60 * 1000),
  },
  {
    id: 'm-101',
    userId: 'u-eli',
    crewId: 'c-capstone',
    body: 'demo prep on friday. who’s in for a late one?',
    sentAt: iso(5 * HOUR),
  },
  {
    id: 'm-102',
    userId: 'u-micah',
    crewId: 'c-capstone',
    body: 'me',
    sentAt: iso(4 * HOUR + 50 * 60 * 1000),
  },
];

export function listMessagesForCrew(crewId: string): ChatMessage[] {
  return chatMessages
    .filter((m) => m.crewId === crewId)
    .sort(
      (a, b) =>
        new Date(a.sentAt).getTime() - new Date(b.sentAt).getTime(),
    );
}

// ---------------------------------------------------------------------------
// Time formatting helpers
// ---------------------------------------------------------------------------

export function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / (60 * 1000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  return `${weeks}w ago`;
}

export function formatClock(iso: string): string {
  const d = new Date(iso);
  let h = d.getHours();
  const m = d.getMinutes();
  const am = h < 12;
  h = h % 12;
  if (h === 0) h = 12;
  return `${h}:${m.toString().padStart(2, '0')} ${am ? 'AM' : 'PM'}`;
}
