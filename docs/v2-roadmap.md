# v2 roadmap

Ideas brainstormed during the v1 design phase that we deliberately deferred to keep the 3-week MVP scope tight. These are good ideas — they're just not v1.

## Social structure

- **Group-formation philosophy** — currently friends-invite-friends via invite code only. v2 questions: should there be in-app admins who curate or approve crews? Should crews be discoverable by topic/interest? Should there be official UATX-sponsored crews vs user-created ones?


- **Time-locked group memberships** — users stick with one crew for a fixed duration (e.g. 4 weeks) before they can leave or switch. Forces deeper accountability.
- **Achievement-gated group switching** — you have to unlock certain achievements before you're allowed to leave or join another crew.
- **Performance-based matchmaking** — algorithm assigns users to crews with people who have similar accumulated sleep scores, rotating periodically.
- **Mixed-tier rotation** — every few weeks, the system reshuffles crews to mix high performers with people who need support.
- **Single-crew enforcement** — a user can only be in one crew at a time, system-enforced.

## Sleep data

- **Naps as a separate post type** — currently excluded entirely; could add a `naps` table or a `kind` column (`'night' | 'nap'`) on posts.
- **Subjective sleep-quality self-rating** — let users rate their sleep on a 1-100 or great/good/rough scale even when no tracker is connected.
- **Per-tracker quality score normalization** — store the raw tracker-reported quality score and normalize it across vendors so cross-Whoop/Oura/Fitbit comparisons are fair.

## Multi-category health data

The whiteboard pitch included far more than sleep. v2 candidates:

- **Workouts** — type, duration, distance, reps, sets, heart rate
- **Heart rate / HRV** — time-series data across days
- **Food** — meals, macros, calorie intake (with photo upload)
- **Weight** — daily entries
- **Mental health check-ins** — short daily mood/stress logs
- **Steps** — daily counts
- **Calories burned**

Each would likely be its own table, linked to the user. Could be added without breaking the v1 sleep schema.

## Privacy & visibility

- **Per-data-category sharing toggles** — let users hide certain data types (e.g. share sleep but not weight).
- **Per-post visibility** — Strava-style "Everyone / Crew / Only me" controls on individual posts.
- **Private notes field on sleep posts** — separate from the public `note` field, only the author sees it.
- **Joiner backfill window** — only show new crew members posts from the last N days, not full history.
- **App-level encryption** — encrypt the dataset at rest beyond what Supabase already provides.

## Engagement & gamification

- **GitHub-style sleep heatmap** — visual calendar grid on profile pages showing which nights the user posted, color-intensity reflecting sleep quality or duration. Like GitHub's contribution graph but for sleep.


- **Achievement system** — badges for milestones (first 7-day streak, perfect week, etc.).
- **Persistent competitions** — turn rolling leaderboards into named, time-bounded competitions with start/end dates, winners, history.
- **Multiple leaderboard categories** — most consistent sleeper, most REM, most deep, best efficiency, longest streak — each its own ranking.
- **Comments / threaded discussion** on sleep posts (currently only reactions).

## Integrations

- **HealthKit bridge** — real-time sleep data import from Apple Health.
- **Tracker integrations** — Whoop, Oura, Fitbit, Garmin, Amazfit, Coros direct API connections.
- **Photo uploads** — Strava-style activity photos, food pics (would require Supabase Storage).

## Infrastructure

- **Push notifications** — currently realtime only works while user has the app open.
- **Email digests** — weekly summary emails.
- **Native iOS app** — currently web-only PWA.
- **Multi-group post broadcasting** — currently sleep is user-scoped and visible in all crews; could let users post to a specific subset of crews.
- **Admin / moderation tooling** — for when the app scales.
