# synzoia

Our final project for the University of Austin (UATX) Spring 2026 Software Engineering course is synzoia, a social media platform that aims to promote healthy habits through accountability. An iOS Shortcut on each person's phone posts HealthKit data to the API. From there, the web app turns it into a chronological feed with milestones, a daily recap post, and a rolling 30-day leaderboard where friends can compete with each other to log the most steps and optimize both their quantity and quality of sleep.

**Live URL**: https://synzoia.vercel.app
**GitHub**: https://github.com/rmbriggs/synzoia
**Tier**: Gold

## Team

- **Angela Lu** handled all things integrations. She built the iPhone Shortcuts responsible for automatically pulling our Apple Health sleep and step data and posting it to synzoia. She also built a Claude AI bot for our team's iMessage group chat (intended to function as a prototype of our app) to keep track of our daily habits while we were building synzoia.
- **Micah Briggs** handled all things frontend. Every single page that you see on the website—landing, signup, the live-updating feed, leaderboard, user profiles, all-members list, and a developer view of the database—was built and designed by Micah. He set up the hosting infrastructure for the website and oversaw the team's pull requests prior to merging.
- **Max Weinstein** handled all things backend. He designed the database schema, built the endpoints to receive sleep and step data from the iPhone Shortcuts that Angela designed, and built the logic that takes Apple Health's raw sleep data and translates it into clear and detailed data, making design decisions around how to differentiate between nights of sleep, naps, and even how to deal with re-posts of the same night.
- **Samuel McClure** handled all things funding and ops. He handled all things pertaining to pitching our project and securing more funding to further develop the app.

## Nontrivial logic

**Bronze: sleep stage sessionization.** The raw Apple Health data did not give us clear "nights" of sleep. It fed us a stream of different types of sleep (REM, Core, Deep, Awake) which could also include data from daytime naps. We built the function `ingest_payload` in `backend/app/services/sleep_sessions.py` to convert that raw stream into clean per-night data. Specifically, this function splits the raw stream into separate sleep sessions if there's more than an hour-long gap, and deems it a night of sleep or a nap based on the time it was recorded. It then totals up the time in each stage, marks the session as currently "in progress" if the person woke up within the past 30 minutes and as "final" if otherwise. Since the iPhone Shortcut runs every 30 minutes (so if you sleep 7 hours then it'll post to the server roughly 14 times), the function checks if the incoming data overlaps an existing session, or in other words, if it's still the same night of sleep. If it is, then it updates that existing session row in the database as opposed to creating a new one. If there is no overlap, then it is a brand new night of sleep or a daytime nap or the previous session ended more than an hour ago, in which case it starts a fresh session row in the database.

**Silver: rolling-30-day capped step leaderboard.** The function `get_global_ranking` in `backend/app/services/steps.py` produces the leaderboard's ordering. It does this by summing each user's step counts over the last 30 days and sorts by total. One of the key design calls we made was setting a cap on each individual day using the `cap_and_sum` helper in `backend/app/services/windows.py`. We did this because we wanted our app to promote consistency over intensity. It's great if someone decides to randomly walk 50k steps in one day but if that person immediately falls off thereafter, the person who gets 10k steps consistently ought to be recognized more in that regard.

**Gold: real-time push.** The Feed page of our website subscribes to a Supabase Realtime channel on the posts table, meaning new posts will populate the browser within roughly a second of being inserted. Thus, there is no need for a manual refresh.

**Custom feature support: milestone + recap post generation.** We developed two server-side functions to enable our timeline to automatically continue moving without someone needing to manually post. `detect_and_insert_milestone` in `backend/app/services/steps.py` runs after every step write, meaning it inserts a post celebrating someone's daily milestone like 10k steps. But it is built to make sure that it evaluates existing milestones already passed so that it doesn't celebrate the same milestone twice. `write_daily_recap` in `backend/app/services/cron.py` tells Vercel every morning to compute yesterday's top-3 step walkers and creates a feed post showing the ranking. Before posting the ranking, it checks the database to make sure it's not making a duplicate.

## Design decisions

**Universal feed table instead of per-type tables.** Every feed item is housed in one shared posts table with a type column that says what type of feed item it is, plus a JSON column to store the type-specific data. Adding a new kind of post is therefore relatively simple: a new type label plus a tiny piece of frontend code is all the system needs to know how to display it. An example is if we wanted to add workouts to the feed, we'd just label the row `type = 'workout'`, store the details in the JSON column like `{kind: "run", distance_mi: 3.2, duration_min: 28}`, and write a small renderer that displays it as "@max ran 3.2 mi in 28 min." This is much simpler as it, again, does not require any backend or database work.

**Bearer-token API-key auth, not Supabase Auth.** Each user gets a personal token that the Shortcut sends with every request. Our server then checks if the token matches a user in the database to determine who is posting. For the purposes of our demo, we made the sign-in process simple on our web app and all it does is remember the current username in its local storage. We wanted to keep the demo as simple as possible so we kept our full Supabase Auth implementation as a PR that can be merged at any time.

**Central Time everywhere, not UTC.** Every date in the app runs on Central Time. We decided to do this because everyone in our group lives within the CT time zone. Using UTC would've proven quite problematic because the boundary at which point it is considered a new day would happen when it was still the evening for us, meaning step and sleep counts could end up on different days, thus breaking the entire database. Concretely, if Max goes on an evening walk at 8 PM CT on a Monday and amasses 10k steps, that should fall under Monday's activity. But from the perspective of UTC, that would be read as Tuesday's activity.

**`NullPool` + Supabase pgbouncer.** Our backend runs on Vercel as "serverless functions," meaning every API request spins up a fresh Python instance, handles the work, and shuts down. That breaks the typical pattern of just having the database connections constantly open for reuse and means that those connections would get orphaned every time a function ended, which would eventually fill up all of the remaining available slots in the database and crash the app. We fixed this by turning pooling off and routing every query through Supabase's built-in pgbouncer. This acts as a middleman, sitting next to the database and managing the connection pool for us. Because pgbouncer is constantly there, the database leak is no longer a problem because now the database perceives a stable client.

## Where Claude helped and where we needed to step in and override its design decisions

Claude was great at expediting the process of writing the actual code, especially in cases where the design call was clear and obvious. It was also great at catching minor things that an engineer might easily forget to implement, like "required" markers on columns or missing database permission rules. We also leveraged Claude as an intellectual sparring partner as we were brainstorming different ways to organize the tables on the backend schema.

Now, we pushed back when it wanted to copy usernames into every post, claiming that it was for the sake of "post performance" which simply was not a plausible reason. It also was trying to leverage useEffect(fetch) but we pushed back and argued that React Query was much simpler and cleaner of a tool. There was no need to overcomplicate things when the tools in place were fine. It even suggested Socket.IO once even though we already had Supabase Realtime set up. Perhaps the most shocking thing was when it tried to wrap every endpoint in error-handling that would effectively make it nearly impossible to spot real problems in the database.

Put simply, Claude was great at expediting the process but it made a ton of poor design decisions that we had to spend a great deal of time arguing with it and overriding its decisions.

## Run locally

```bash
# clone + install
git clone https://github.com/rmbriggs/synzoia.git
cd synzoia
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
(cd frontend && npm install)

# env (backend/.env)
DATABASE_URL=postgresql+psycopg://...:6543/postgres  # Supabase pooler
CRON_SECRET=...                                      # for /api/cron/daily-recap
STEPS_DAILY_CAP=25000

# env (frontend/.env)
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=...
VITE_API_BASE=http://localhost:8000

# migrate: paste each backend/migrations/*.sql file into the Supabase
# SQL Editor in numeric order (0001 → 0011). The files are idempotent —
# safe to re-run. We use raw SQL rather than Alembic so the migration
# history is also a readable spec.

# run
(cd backend && uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev)

# tests
(cd backend && pytest)
(cd frontend && npm test)
```

## Gold features

**Real-time push updates via Supabase Realtime.** When the feed page renders, the browser starts a live connection to Supabase. When anyone tries to create a new post, the connection fires and causes the feed to reload automatically. When you exit the page, that connection ceases to exist. The settings on the Supabase-side are written into migration 0010 so this works on any deploy.

**Custom 1: auto-generated activity feed.** The feed is not just stuff that users post manually. Two server-side functions write to it automatically: `detect_and_insert_milestone` in `backend/app/services/steps.py` celebrates when a user hits a daily step milestone (1k, 5k, or 10k), and `write_daily_recap` in `backend/app/services/cron.py` runs every morning at 11 UTC and posts a "yesterday's top 3" recap. These auto-posts route through the same posts table the real-time channel watches, so they just show up in every browser the same way manual posts do.

**Custom 2: hover-intent prefetch on the Users page.** When you hover over a user in the Users list for more than 100ms, the browser will start fetching the user's profile data, meaning that by the time you click, the data is already there. But if you move your cursor away within 100ms, the prefetch cancels.
