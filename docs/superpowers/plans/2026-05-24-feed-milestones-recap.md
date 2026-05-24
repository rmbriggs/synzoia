# Feed milestones + 6am leaderboard recap — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/feed` page's leaderboard view with a chronological post stream powered by two new event sources: per-day step-milestone posts (1k/5k/10k) and a 6am-CT daily-recap post written by a Vercel cron.

**Architecture:** Three independent PRs. (1) Backend migration 0007 adds `details jsonb` + `body text` columns to `posts` and extends the type CHECK; the `POST /api/steps` handler grows a milestone-detection step that inserts ONE post per write for the highest newly-crossed threshold. (2) New `GET /api/cron/daily-recap` endpoint, secured by a Bearer-`CRON_SECRET`, computes yesterday's CT-bucketed top 3 and writes a `leaderboard_recap` post. Vercel cron fires it at 11 UTC year-round. (3) Frontend gets an `api/posts.ts` wrapper and a rewritten `Feed.tsx` that fans the post list out into type-specific renderers.

**Tech Stack:** FastAPI + SQLAlchemy + psycopg v3 (backend), React + Vite + React Query + Tailwind (frontend), Supabase Postgres, Vercel hosting + cron.

**Spec:** `docs/superpowers/specs/2026-05-24-feed-milestones-recap-design.md`

---

## File Structure

### PR 1 — backend: schema + milestones (branch `feat/post-milestones`)

| File | Action | Responsibility |
|---|---|---|
| `backend/migrations/0007_post_details_and_body.sql` | create | Add `details jsonb`, `body text`; extend type CHECK |
| `backend/app/schemas/posts.py` | modify | Extend `PostType` Literal; add `details` + `body` to `PostResponse` |
| `backend/app/services/posts.py` | modify | Include `details` + `body` in SELECT/RETURNING; populate `PostResponse` |
| `backend/app/services/steps.py` | modify | Add `MILESTONE_THRESHOLDS` constant + `detect_and_insert_milestone` helper |
| `backend/app/routes/steps.py` | modify | Call milestone helper inside `create_step` (same transaction) |
| `backend/tests/test_steps_write.py` | modify | 4 new tests for milestone detection |
| `backend/tests/test_posts_routes.py` | modify | Update PostResponse expectations to include null `details` + `body` |

### PR 2 — backend: cron (branch `feat/daily-recap-cron`)

| File | Action | Responsibility |
|---|---|---|
| `backend/.env.example` | modify | Document `CRON_SECRET` |
| `backend/app/services/cron.py` | create | `write_daily_recap(conn, today)` business logic |
| `backend/app/routes/cron.py` | create | `GET /api/cron/daily-recap` endpoint + `_verify_cron_secret` |
| `backend/app/main.py` | modify | Include the cron router |
| `backend/tests/test_cron_routes.py` | create | 4 tests: happy path, no-data, already-posted, auth-fail |
| `vercel.json` | modify | Add `crons` block at `0 11 * * *` |

### PR 3 — frontend: Feed rewrite (branch `feat/feed-post-stream`)

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/api/posts.ts` | create | `getFeed` + `getUserFeed` + post-type interfaces |
| `frontend/src/lib/dates.ts` | modify | Add `formatRelative(iso, now?)` helper |
| `frontend/src/pages/Feed.tsx` | rewrite | Render chronological post stream; type-specific row components |
| `frontend/src/__tests__/Feed.test.tsx` | rewrite | 5 tests for the new stream |
| `frontend/src/__tests__/dates.test.ts` | create | Tests for `formatRelative` |

---

# PR 1 — Backend: schema + milestones

### Task 1.0: Branch

- [ ] **Step 1: Create the branch**

```bash
git checkout main && git pull --ff-only
git checkout -b feat/post-milestones
```

### Task 1.1: Write migration 0007

**Files:**
- Create: `backend/migrations/0007_post_details_and_body.sql`

- [ ] **Step 1: Create the file**

```sql
-- ============================================================================
-- 0007_post_details_and_body.sql
-- ============================================================================
-- Adds two payload columns to `posts` so feed events can carry the
-- data their renderers need, and extends the type CHECK with the two
-- new event types this PR introduces.
--
-- Columns added:
--   details  JSONB  — structured payload, type-specific. Nullable.
--                      Examples:
--                        steps_milestone:  {"threshold": 5000, "date": "2026-05-23"}
--                        leaderboard_recap:{"date": "2026-05-23",
--                                            "top": [{"username": "...", "total": 9567}, ...]}
--   body     TEXT   — pre-rendered display caption. Nullable.
--                      Examples:
--                        steps_milestone:  "hit 5,000 steps"
--                        leaderboard_recap:"Yesterday's top 3"
--
-- New types in the CHECK constraint:
--   steps_milestone   — a user crossed 1k/5k/10k today
--   leaderboard_recap — the 6am daily top-3 recap (system-generated)
--
-- Existing types (sleep, steps, workout) are preserved.
-- ============================================================================

alter table posts add column details jsonb;
alter table posts add column body    text;

alter table posts drop constraint if exists posts_type_check;
alter table posts add constraint posts_type_check
  check (type in (
    'sleep', 'steps', 'workout',
    'steps_milestone',
    'leaderboard_recap'
  ));
```

- [ ] **Step 2: Commit**

```bash
git add backend/migrations/0007_post_details_and_body.sql
git commit -m "feat(db): migration 0007 — posts.details + posts.body + new types"
```

### Task 1.2: Extend Pydantic schema

**Files:**
- Modify: `backend/app/schemas/posts.py`

- [ ] **Step 1: Update PostType Literal and PostResponse**

Replace the existing `PostType` and `PostResponse` definitions in `backend/app/schemas/posts.py`:

```python
from typing import Any, Literal, Optional

PostType = Literal[
    "sleep",
    "steps",
    "workout",
    "steps_milestone",
    "leaderboard_recap",
]


class PostResponse(BaseModel):
    """Single row representation, returned by POST /api/posts and
    embedded in feed list responses."""

    id: int
    user_id: int
    username: str
    type: PostType
    timestamp: datetime
    details: Optional[dict[str, Any]] = None
    body: Optional[str] = None
```

Keep `CreatePostRequest` and `FeedResponse` unchanged.

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/posts.py
git commit -m "feat(schemas): extend PostType + add details/body to PostResponse"
```

### Task 1.3: Update services/posts to read new columns

**Files:**
- Modify: `backend/app/services/posts.py`

- [ ] **Step 1: Update list_feed SELECTs to include details + body**

In `list_feed`, both SQL branches (no filter and type filter) currently select `id, user_id, username, type, timestamp`. Add `details, body` to both. Example for the no-filter branch:

```python
rows = (
    conn.execute(
        text(
            "SELECT id, user_id, username, type, timestamp, details, body "
            "FROM posts "
            "ORDER BY timestamp DESC, id DESC "
            "LIMIT :limit"
        ),
        {"limit": capped},
    )
    .mappings()
    .all()
)
```

Apply the same change to the `type_filter is not None` branch.

- [ ] **Step 2: Update list_user_feed SELECT similarly**

```python
rows = (
    conn.execute(
        text(
            "SELECT id, user_id, username, type, timestamp, details, body "
            "FROM posts "
            "WHERE user_id = :uid "
            "ORDER BY timestamp DESC, id DESC "
            "LIMIT :limit"
        ),
        {"uid": int(profile["id"]), "limit": capped},
    )
    .mappings()
    .all()
)
```

- [ ] **Step 3: Update create_post RETURNING**

```python
row = (
    conn.execute(
        text(
            "INSERT INTO posts (user_id, username, type, timestamp) "
            "VALUES (:user_id, :username, :type, :timestamp) "
            "RETURNING id, user_id, username, type, timestamp, details, body"
        ),
        ...
    )
    .mappings()
    .one()
)
```

- [ ] **Step 4: Update both PostResponse constructors to include details + body**

In `list_feed`, `list_user_feed`, AND `create_post`:

```python
PostResponse(
    id=int(r["id"]),
    user_id=int(r["user_id"]),
    username=r["username"],
    type=r["type"],
    timestamp=r["timestamp"],
    details=r["details"],
    body=r["body"],
)
```

(In `create_post`, replace `row` for `r`.)

- [ ] **Step 5: Run posts tests to verify nothing regressed**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_posts_routes.py -v
```

Expected: PASS (existing test rows have `details=null` and `body=null` after migration; the JSON response now includes those keys with null values, which is what the assertions allow).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/posts.py
git commit -m "feat(services/posts): read + return details and body columns"
```

### Task 1.4: Milestone detection helper — failing test

**Files:**
- Test: `backend/tests/test_steps_write.py`

- [ ] **Step 1: Read the existing test_steps_write.py to find the `_engine_with_users` fixture**

```bash
cat backend/tests/test_steps_write.py | head -60
```

The fixture defines `profiles` and `steps` tables but NOT `posts`. We need a fixture that also creates `posts` with the post-0007 schema. Add a new helper next to `_engine_with_users`.

- [ ] **Step 2: Add a posts-aware engine fixture and 4 milestone tests at the bottom of `backend/tests/test_steps_write.py`**

```python
def _engine_with_users_and_posts():
    """Same as _engine_with_users but also creates the posts table
    (post-migration-0007 shape) so milestone-detection tests can
    observe what got inserted."""
    engine = _engine_with_users()
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE posts ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "username text not null, "
                "type text not null, "
                "timestamp text not null, "
                "details text, "  # SQLite has no jsonb; store as text
                "body text)"
            )
        )
    return engine


def _milestone_rows(engine, user_id: int):
    with engine.connect() as conn:
        return list(
            conn.execute(
                text(
                    "SELECT id, type, body, details FROM posts "
                    "WHERE type = 'steps_milestone' AND user_id = :uid "
                    "ORDER BY id ASC"
                ),
                {"uid": user_id},
            )
            .mappings()
            .all()
        )


def test_step_write_below_1k_inserts_no_milestone(monkeypatch):
    engine = _engine_with_users_and_posts()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T18:00:00", "total": 900},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    assert _milestone_rows(engine, user_id=1) == []


def test_step_write_crossing_1k_inserts_one_milestone(monkeypatch):
    engine = _engine_with_users_and_posts()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T18:00:00", "total": 1200},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    rows = _milestone_rows(engine, user_id=1)
    assert len(rows) == 1
    assert rows[0]["body"] == "hit 1,000 steps"
    # details is JSON text in SQLite; parse to check
    import json as _json
    assert _json.loads(rows[0]["details"]) == {
        "threshold": 1000,
        "date": "2026-05-23",
    }


def test_step_write_zero_to_12k_in_one_shot_picks_highest_only(monkeypatch):
    engine = _engine_with_users_and_posts()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T18:00:00", "total": 12000},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    rows = _milestone_rows(engine, user_id=1)
    assert len(rows) == 1
    assert rows[0]["body"] == "hit 10,000 steps"


def test_step_write_above_5k_twice_only_inserts_one_milestone(monkeypatch):
    engine = _engine_with_users_and_posts()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    first = client.post(
        "/api/steps",
        json={"timestamp": "2026-05-23T18:00:00", "total": 5500},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )
    second = client.post(
        "/api/steps",
        json={"timestamp": "2026-05-23T20:00:00", "total": 6800},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    rows = _milestone_rows(engine, user_id=1)
    # First write crosses 1k + 5k → posts highest (5k). Second crosses
    # nothing new → no post. So exactly one row.
    assert len(rows) == 1
    assert rows[0]["body"] == "hit 5,000 steps"
```

- [ ] **Step 3: Run the tests and confirm they fail**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_steps_write.py -v -k "milestone"
```

Expected: 4 tests FAIL. They will fail because the milestone helper doesn't exist yet — POST /api/steps returns 201 but no post rows get created.

### Task 1.5: Implement milestone detection helper

**Files:**
- Modify: `backend/app/services/steps.py`

- [ ] **Step 1: Add `MILESTONE_THRESHOLDS` constant and `detect_and_insert_milestone` helper**

Add these next to `OUTLIER_CAP` (after the `_utc_window` helper, before the `_lookup_user` helper) in `backend/app/services/steps.py`:

```python
import json as _json

# Step counts at which the feed celebrates the user's day. Per-day,
# per-user, per-threshold idempotent — once crossed today, the same
# threshold won't fire again until tomorrow CT.
MILESTONE_THRESHOLDS = (1000, 5000, 10000)


def detect_and_insert_milestone(
    conn: Connection,
    user_id: int,
    timestamp: datetime,
) -> int | None:
    """After inserting a step row, check whether the user just crossed
    a milestone threshold for the CT day this step bucketed to. If yes,
    insert ONE post for the HIGHEST newly-crossed threshold and return
    the new post's id. Otherwise return None.

    Idempotent: existing milestone posts for the same user on the same
    CT date short-circuit re-firing of their thresholds. So a write
    that takes the user from 5500 to 6000 doesn't re-fire the 5k post."""
    ct_date = _ct_date(timestamp)
    lower, upper = _utc_window(ct_date, ct_date)

    max_today_row = (
        conn.execute(
            text(
                "SELECT MAX(total) AS m FROM steps "
                "WHERE user_id = :uid "
                "AND timestamp >= :lower AND timestamp < :upper "
                "AND total <= :cap"
            ),
            {"uid": user_id, "lower": lower, "upper": upper, "cap": OUTLIER_CAP},
        )
        .mappings()
        .first()
    )
    max_today = int(max_today_row["m"] or 0)

    # Already-crossed thresholds for this user on this CT date.
    # Works against both Postgres (jsonb -> text via ->>) and the
    # SQLite test fixture (where `details` is a text column holding
    # a JSON string).
    already_rows = (
        conn.execute(
            text(
                "SELECT details FROM posts "
                "WHERE type = 'steps_milestone' "
                "AND user_id = :uid"
            ),
            {"uid": user_id},
        )
        .mappings()
        .all()
    )
    already_crossed: set[int] = set()
    for r in already_rows:
        raw = r["details"]
        if raw is None:
            continue
        d = _json.loads(raw) if isinstance(raw, str) else raw
        if d.get("date") == ct_date.isoformat() and "threshold" in d:
            already_crossed.add(int(d["threshold"]))

    newly_crossed = [
        t
        for t in MILESTONE_THRESHOLDS
        if t <= max_today and t not in already_crossed
    ]
    if not newly_crossed:
        return None

    threshold = max(newly_crossed)
    username_row = (
        conn.execute(
            text("SELECT username FROM profiles WHERE id = :uid"),
            {"uid": user_id},
        )
        .mappings()
        .first()
    )
    if username_row is None:
        return None  # User vanished between insert and detect; bail.
    username = username_row["username"]

    details_str = _json.dumps(
        {"threshold": threshold, "date": ct_date.isoformat()}
    )
    body = f"hit {threshold:,} steps"

    row = (
        conn.execute(
            text(
                "INSERT INTO posts (user_id, username, type, timestamp, details, body) "
                "VALUES (:uid, :u, 'steps_milestone', :ts, :details, :body) "
                "RETURNING id"
            ),
            {
                "uid": user_id,
                "u": username,
                "ts": timestamp,
                "details": details_str,
                "body": body,
            },
        )
        .mappings()
        .one()
    )
    return int(row["id"])
```

- [ ] **Step 2: Wire into POST /api/steps**

In `backend/app/routes/steps.py`, locate `create_step` and update the body:

```python
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateStepResponse,
)
def create_step(
    req: CreateStepRequest,
    user_id: int = Depends(require_user),
) -> CreateStepResponse:
    """POST /api/steps — write a step snapshot on behalf of the
    Bearer-token user. Called by the iOS Shortcut every time Apple
    Health step data is synced. `user_id` is resolved from the token,
    NEVER from the request body (per CLAUDE.md). Also fires
    milestone-detection in the same transaction."""
    with db.get_engine().begin() as conn:
        response = svc.create_step(
            conn,
            user_id=user_id,
            timestamp=req.timestamp,
            total=req.total,
        )
        svc.detect_and_insert_milestone(
            conn,
            user_id=user_id,
            timestamp=req.timestamp,
        )
        return response
```

- [ ] **Step 3: Run the milestone tests; they should now pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_steps_write.py -v
```

Expected: ALL tests in `test_steps_write.py` PASS, including the new milestone ones.

- [ ] **Step 4: Run the full backend test suite**

```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/steps.py backend/app/routes/steps.py backend/tests/test_steps_write.py
git commit -m "feat(steps): insert steps_milestone post on threshold crossing"
```

### Task 1.6: Push + open PR + apply migration

- [ ] **Step 1: Push**

```bash
git push -u origin feat/post-milestones
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "feat(backend): post details/body + steps_milestone on threshold crossings" --body "$(cat <<'EOF'
First of three PRs in the feed-redesign slice (spec: docs/superpowers/specs/2026-05-24-feed-milestones-recap-design.md).

- Migration 0007 adds `details jsonb` + `body text` to posts and extends the type CHECK with `steps_milestone` + `leaderboard_recap`.
- services/posts.py SELECTs + PostResponse pick up the new columns.
- New `detect_and_insert_milestone(conn, user_id, timestamp)` helper in services/steps.py runs inside the POST /api/steps transaction. Inserts ONE post per write for the highest newly-crossed threshold; idempotent per (user, day, threshold).
- 4 new tests in test_steps_write.py; existing 55 backend tests still green.

After merge: apply 0007 to live Supabase via MCP.
EOF
)"
```

- [ ] **Step 3: Wait for CI green; merge**

```bash
gh pr checks <PR#> --watch --interval 8
gh pr merge <PR#> --squash --delete-branch
```

- [ ] **Step 4: Apply migration 0007 to live Supabase via MCP**

Use the `mcp__plugin_supabase_supabase__apply_migration` tool with `project_id="yrerlndtavoxbocizjfq"` and `name="0007_post_details_and_body"`, passing the SQL from `backend/migrations/0007_post_details_and_body.sql`.

- [ ] **Step 5: Verify live**

```bash
curl https://synzoia.vercel.app/api/health/db
```

Expected: `{"ok": true, "stage": "query", "tables": {"profiles": ..., "steps": ..., "posts": ...}}`.

---

# PR 2 — Backend: daily-recap cron

### Task 2.0: Branch from updated main

- [ ] **Step 1: Branch**

```bash
git checkout main && git pull --ff-only
git checkout -b feat/daily-recap-cron
```

### Task 2.1: Document CRON_SECRET in .env.example

**Files:**
- Modify: `backend/.env.example`

- [ ] **Step 1: Append CRON_SECRET to .env.example**

```bash
cat >> backend/.env.example <<'EOF'

# Shared secret Vercel cron sends in `Authorization: Bearer <CRON_SECRET>`.
# Set the same value on Vercel (Settings -> Environment Variables) for
# Production / Preview / Development scopes. Any random 32+ char string is
# fine (e.g. output of `openssl rand -hex 32`).
CRON_SECRET=
EOF
```

- [ ] **Step 2: Commit**

```bash
git add backend/.env.example
git commit -m "docs(env): CRON_SECRET for daily-recap cron auth"
```

### Task 2.2: Daily-recap service — failing test

**Files:**
- Test: `backend/tests/test_cron_routes.py`

- [ ] **Step 1: Create the test file**

```python
"""HTTP-level tests for /api/cron/daily-recap.

Exercises the wire: secret-authed write of a leaderboard_recap post
for yesterday's top 3, idempotency when called twice, the no-data
short-circuit, and the 401 path for missing/wrong auth."""

import json
import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


CRON_SECRET = "test_cron_secret_value"


def _engine_with_yesterday_data(seed_rows=True):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE profiles ("
                "id integer primary key autoincrement, "
                "username text not null unique, "
                "token text not null unique, "
                "join_date text not null default (datetime('now')))"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE steps ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "timestamp text not null, "
                "total integer not null)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE posts ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "username text not null, "
                "type text not null, "
                "timestamp text not null, "
                "details text, "
                "body text)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) "
                "VALUES ('micah', 'tm', '2026-05-01T00:00:00'), "
                "('angela', 'ta', '2026-05-01T00:00:00'), "
                "('bob', 'tb', '2026-05-01T00:00:00')"
            )
        )
        if seed_rows:
            # Yesterday CT = 2026-05-22 (we'll have the cron treat
            # today_ct = 2026-05-23). Timestamps stored as UTC,
            # bucketed to CT via the existing _ct_date helper. UTC
            # afternoon = CT morning of the same day.
            conn.execute(
                text(
                    "INSERT INTO steps (user_id, timestamp, total) VALUES "
                    "(1, '2026-05-22T18:00:00', 12000), "
                    "(2, '2026-05-22T18:00:00', 9500), "
                    "(3, '2026-05-22T18:00:00', 4200)"
                )
            )
    return engine


def _post_rows(engine, type_filter=None):
    with engine.connect() as conn:
        if type_filter:
            return list(
                conn.execute(
                    text(
                        "SELECT id, type, body, details FROM posts "
                        "WHERE type = :t ORDER BY id ASC"
                    ),
                    {"t": type_filter},
                )
                .mappings()
                .all()
            )
        return list(
            conn.execute(text("SELECT id, type FROM posts ORDER BY id ASC"))
            .mappings()
            .all()
        )


def test_daily_recap_inserts_top3_for_yesterday(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    engine = _engine_with_yesterday_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    # Pin "today" to a known date so we can predict "yesterday".
    from backend.app.routes import cron as cron_routes
    from datetime import date

    monkeypatch.setattr(cron_routes, "_today_ct", lambda: date(2026, 5, 23))

    response = TestClient(main.app).get(
        "/api/cron/daily-recap",
        headers={"Authorization": f"Bearer {CRON_SECRET}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "inserted" in body

    rows = _post_rows(engine, type_filter="leaderboard_recap")
    assert len(rows) == 1
    details = json.loads(rows[0]["details"])
    assert details["date"] == "2026-05-22"
    assert [t["username"] for t in details["top"]] == ["micah", "angela", "bob"]
    assert [t["total"] for t in details["top"]] == [12000, 9500, 4200]
    assert rows[0]["body"] == "Yesterday's top 3"


def test_daily_recap_skipped_when_no_data(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    engine = _engine_with_yesterday_data(seed_rows=False)
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    from backend.app.routes import cron as cron_routes
    from datetime import date

    monkeypatch.setattr(cron_routes, "_today_ct", lambda: date(2026, 5, 23))

    response = TestClient(main.app).get(
        "/api/cron/daily-recap",
        headers={"Authorization": f"Bearer {CRON_SECRET}"},
    )

    assert response.status_code == 200
    assert response.json() == {"skipped": "no_data"}
    assert _post_rows(engine, type_filter="leaderboard_recap") == []


def test_daily_recap_idempotent_on_second_call(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    engine = _engine_with_yesterday_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    from backend.app.routes import cron as cron_routes
    from datetime import date

    monkeypatch.setattr(cron_routes, "_today_ct", lambda: date(2026, 5, 23))
    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {CRON_SECRET}"}

    first = client.get("/api/cron/daily-recap", headers=headers)
    second = client.get("/api/cron/daily-recap", headers=headers)

    assert first.status_code == 200 and "inserted" in first.json()
    assert second.status_code == 200
    assert second.json() == {"skipped": "already_posted"}
    assert len(_post_rows(engine, type_filter="leaderboard_recap")) == 1


def test_daily_recap_rejects_missing_or_bad_auth(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", CRON_SECRET)
    engine = _engine_with_yesterday_data()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    # No header
    r1 = client.get("/api/cron/daily-recap")
    # Wrong secret
    r2 = client.get(
        "/api/cron/daily-recap", headers={"Authorization": "Bearer wrong"}
    )

    assert r1.status_code == 401
    assert r2.status_code == 401
    assert _post_rows(engine, type_filter="leaderboard_recap") == []
```

- [ ] **Step 2: Run the tests; expect failures**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_cron_routes.py -v
```

Expected: all 4 tests FAIL — `ModuleNotFoundError` on `backend.app.routes.cron` or 404 on the route.

### Task 2.3: Implement services/cron.py

**Files:**
- Create: `backend/app/services/cron.py`

- [ ] **Step 1: Create the file**

```python
"""Daily leaderboard recap.

Run by Vercel cron once a day (see backend/app/routes/cron.py +
vercel.json). Computes yesterday's top 3 step posters in Central
Time and inserts a single `leaderboard_recap` post into the feed.

Idempotent: if a recap for that date already exists, the call is a
no-op. Bail-cleanly: if no one posted yesterday, no post is created."""

from __future__ import annotations

import json as _json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.services import steps as svc_steps


def write_daily_recap(conn: Connection, today: date) -> dict:
    """Insert one `leaderboard_recap` post for (today - 1 day), if one
    doesn't exist yet and there's data to recap. `today` should be the
    CT date — the caller is responsible for that.

    Returns one of:
      {"inserted": {<post row>}}
      {"skipped": "already_posted"}
      {"skipped": "no_data"}
    """
    yesterday = today - timedelta(days=1)
    yesterday_iso = yesterday.isoformat()

    # Idempotency check. Works against Postgres jsonb (->>'date') and
    # the SQLite test fixture (text column with a JSON string).
    existing_rows = (
        conn.execute(
            text(
                "SELECT details FROM posts "
                "WHERE type = 'leaderboard_recap'"
            ),
        )
        .mappings()
        .all()
    )
    for r in existing_rows:
        raw = r["details"]
        if raw is None:
            continue
        d = _json.loads(raw) if isinstance(raw, str) else raw
        if d.get("date") == yesterday_iso:
            return {"skipped": "already_posted"}

    daily_totals = svc_steps._daily_totals_in_range(conn, yesterday, yesterday)
    if not daily_totals:
        return {"skipped": "no_data"}

    usernames = svc_steps._usernames_for(
        conn, {uid for uid, _, _ in daily_totals}
    )
    ranked = sorted(
        ((uid, total) for uid, _, total in daily_totals if uid in usernames),
        key=lambda x: (-x[1], usernames[x[0]]),
    )[:3]
    if not ranked:
        return {"skipped": "no_data"}

    top = [
        {"username": usernames[uid], "total": int(total)}
        for uid, total in ranked
    ]
    top1_uid, top1_total = ranked[0]
    top1_username = usernames[top1_uid]

    details_str = _json.dumps({"date": yesterday_iso, "top": top})
    body = "Yesterday's top 3"
    now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    row = (
        conn.execute(
            text(
                "INSERT INTO posts "
                "(user_id, username, type, timestamp, details, body) "
                "VALUES (:uid, :u, 'leaderboard_recap', :ts, :details, :body) "
                "RETURNING id, user_id, username, type, timestamp, details, body"
            ),
            {
                "uid": top1_uid,
                "u": top1_username,
                "ts": now_utc_naive,
                "details": details_str,
                "body": body,
            },
        )
        .mappings()
        .one()
    )
    return {"inserted": dict(row)}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/cron.py
git commit -m "feat(services/cron): write_daily_recap business logic"
```

### Task 2.4: Implement routes/cron.py

**Files:**
- Create: `backend/app/routes/cron.py`

- [ ] **Step 1: Create the file**

```python
"""HTTP layer for /api/cron/*.

Endpoints are GET-only because Vercel Cron Jobs send GET requests.
Each one verifies a Bearer-CRON_SECRET header (set in Vercel env)
before dispatching to its service."""

import os
import secrets as _secrets
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header

from backend.app import db
from backend.app.errors import AppError
from backend.app.services import cron as svc

router = APIRouter(prefix="/api/cron", tags=["cron"])

APP_TZ = ZoneInfo("America/Chicago")


def _today_ct() -> date:
    """Today's date in app timezone. Pulled out as a module-level
    function so tests can monkeypatch it deterministically."""
    return datetime.now(APP_TZ).date()


def _verify_cron_secret(authorization: Optional[str]) -> None:
    """Reject anything that isn't `Bearer <CRON_SECRET>` (with the
    CRON_SECRET env var matching exactly, constant-time compare)."""
    expected = os.environ.get("CRON_SECRET")
    if not expected:
        # Better to 503 than to allow unauthed cron triggers.
        raise AppError(
            503,
            "cron_misconfigured",
            "CRON_SECRET is not set on the backend.",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(
            401,
            "unauthenticated",
            "Missing or invalid Authorization header.",
        )
    presented = authorization[len("Bearer ") :].strip()
    if not _secrets.compare_digest(presented, expected):
        raise AppError(401, "unauthenticated", "Invalid cron secret.")


@router.get("/daily-recap")
def daily_recap(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Vercel cron entry. Writes a leaderboard_recap post for yesterday
    CT (idempotent) or returns a structured skip reason."""
    _verify_cron_secret(authorization)
    with db.get_engine().begin() as conn:
        return svc.write_daily_recap(conn, today=_today_ct())
```

- [ ] **Step 2: Register the router in main.py**

In `backend/app/main.py`, locate the existing `from backend.app.routes import steps as steps_routes` import and add:

```python
from backend.app.routes import cron as cron_routes
from backend.app.routes import posts as posts_routes
from backend.app.routes import steps as steps_routes
```

And below `app.include_router(steps_routes.router)`:

```python
app.include_router(cron_routes.router)
```

- [ ] **Step 3: Run the cron tests; they should now pass**

```bash
cd backend && source .venv/bin/activate && pytest tests/test_cron_routes.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 4: Run full backend suite**

```bash
cd backend && source .venv/bin/activate && pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/cron.py backend/app/main.py backend/tests/test_cron_routes.py
git commit -m "feat(routes/cron): GET /api/cron/daily-recap with Bearer-secret auth"
```

### Task 2.5: Register cron in vercel.json

**Files:**
- Modify: `vercel.json`

- [ ] **Step 1: Add crons block**

Replace the existing `vercel.json` with:

```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "functions": {
    "api/index.py": {
      "includeFiles": "backend/**"
    }
  },
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/index" },
    { "source": "/(.*)",     "destination": "/index.html" }
  ],
  "crons": [
    { "path": "/api/cron/daily-recap", "schedule": "0 11 * * *" }
  ]
}
```

Note for any reader: `0 11 * * *` UTC = 6am CDT (Mar–Nov) / 5am CST (Nov–Mar). Acceptable for a class-project demo; the schedule could be made DST-aware later if needed.

- [ ] **Step 2: Commit**

```bash
git add vercel.json
git commit -m "chore(vercel): register daily-recap cron at 11 UTC"
```

### Task 2.6: Push + PR + manual env-var setup

- [ ] **Step 1: Push**

```bash
git push -u origin feat/daily-recap-cron
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "feat(backend): daily-recap cron at 11 UTC" --body "$(cat <<'EOF'
Second of three PRs in the feed-redesign slice.

- New GET /api/cron/daily-recap endpoint, secured by Bearer <CRON_SECRET>.
- write_daily_recap(conn, today) computes yesterday's CT top 3 via the existing _daily_totals_in_range helper and inserts ONE leaderboard_recap post. Idempotent per date.
- vercel.json registers the cron at "0 11 * * *" (= 6am CDT / 5am CST).

Before this works in production: set CRON_SECRET as a Vercel env var (Production + Preview + Development scopes). I'll do that after merge.

Tests: 4 new in test_cron_routes.py (happy path, no-data skip, idempotency skip, 401 on missing/bad auth). All backend tests pass.
EOF
)"
```

- [ ] **Step 3: Wait for CI + merge**

```bash
gh pr checks <PR#> --watch --interval 8
gh pr merge <PR#> --squash --delete-branch
```

- [ ] **Step 4: Set CRON_SECRET in Vercel**

Ask the user to:
1. Run `openssl rand -hex 32` to generate a secret.
2. Open Vercel dashboard → synzoia project → Settings → Environment Variables.
3. Add a new variable `CRON_SECRET` with that value, scoped to Production + Preview + Development.
4. Trigger a redeploy (push empty commit OR Redeploy from dashboard).

- [ ] **Step 5: Verify after the redeploy lands**

Wait for Vercel deploy. Then:

```bash
# Should 401 — no auth.
curl -i https://synzoia.vercel.app/api/cron/daily-recap

# With the right secret, should return either an inserted post,
# already_posted skip, or no_data skip — depending on what was
# in the steps table yesterday CT.
curl -i https://synzoia.vercel.app/api/cron/daily-recap \
  -H "Authorization: Bearer $(your CRON_SECRET value)"
```

---

# PR 3 — Frontend: Feed rewrite

### Task 3.0: Branch from updated main

- [ ] **Step 1: Branch**

```bash
git checkout main && git pull --ff-only
git checkout -b feat/feed-post-stream
```

### Task 3.1: api/posts.ts wrapper

**Files:**
- Create: `frontend/src/api/posts.ts`

- [ ] **Step 1: Create the file**

```typescript
import { apiFetch } from './client';

export type PostType =
  | 'sleep'
  | 'steps'
  | 'workout'
  | 'steps_milestone'
  | 'leaderboard_recap';

export interface PostDetails {
  threshold?: number;
  date?: string;
  top?: { username: string; total: number }[];
}

export interface FeedPost {
  id: number;
  user_id: number;
  username: string;
  type: PostType;
  timestamp: string;
  details: PostDetails | null;
  body: string | null;
}

export interface FeedResponse {
  posts: FeedPost[];
}

export function getFeed(limit?: number): Promise<FeedResponse> {
  const qs = limit ? `?limit=${limit}` : '';
  return apiFetch<FeedResponse>(`/posts${qs}`);
}

export function getUserFeed(
  username: string,
  limit?: number,
): Promise<FeedResponse> {
  const qs = limit ? `?limit=${limit}` : '';
  return apiFetch<FeedResponse>(
    `/posts/users/${encodeURIComponent(username)}${qs}`,
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/posts.ts
git commit -m "feat(api/posts): client wrapper for the feed endpoints"
```

### Task 3.2: formatRelative helper — failing test

**Files:**
- Test: `frontend/src/__tests__/dates.test.ts`

- [ ] **Step 1: Create the test file**

```typescript
import { describe, expect, it } from 'vitest';
import { formatRelative } from '@/lib/dates';

describe('formatRelative', () => {
  const now = new Date('2026-05-24T15:00:00Z'); // 10am CT

  it('returns "just now" within the same minute', () => {
    const just = new Date('2026-05-24T14:59:45Z').toISOString();
    expect(formatRelative(just, now)).toBe('just now');
  });

  it('returns "Nm ago" for less than an hour', () => {
    const fifteenMin = new Date('2026-05-24T14:45:00Z').toISOString();
    expect(formatRelative(fifteenMin, now)).toBe('15m ago');
  });

  it('returns "Nh ago" for less than a day', () => {
    const threeH = new Date('2026-05-24T12:00:00Z').toISOString();
    expect(formatRelative(threeH, now)).toBe('3h ago');
  });

  it('returns "yesterday" for the previous CT day', () => {
    // 2026-05-24T01:00:00Z = 2026-05-23 20:00 CT (yesterday in CT)
    const yesterdayCT = new Date('2026-05-24T01:00:00Z').toISOString();
    expect(formatRelative(yesterdayCT, now)).toBe('yesterday');
  });

  it('returns a "Month Day" string for older posts', () => {
    const old = new Date('2026-05-21T15:00:00Z').toISOString();
    expect(formatRelative(old, now)).toMatch(/May 21/);
  });
});
```

- [ ] **Step 2: Run the test; expect failure**

```bash
cd frontend && npm test -- --run dates.test.ts
```

Expected: FAIL — `formatRelative` is not exported from `@/lib/dates`.

### Task 3.3: Implement formatRelative

**Files:**
- Modify: `frontend/src/lib/dates.ts`

- [ ] **Step 1: Add the helper at the bottom of `frontend/src/lib/dates.ts`**

```typescript
const CT_YMD = new Intl.DateTimeFormat('en-CA', {
  timeZone: APP_TIMEZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

/**
 * Render a short relative time for the feed: "just now", "5m ago",
 * "2h ago", "yesterday", "May 21". Anchored to CT for the day-bucket
 * decisions so "today" and "yesterday" line up with the user's wall
 * clock, not their browser's.
 */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const then = new Date(iso);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60_000);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;

  const thenDate = CT_YMD.format(then);
  const nowDate = CT_YMD.format(now);
  const yesterday = CT_YMD.format(new Date(now.getTime() - 86_400_000));

  if (thenDate === nowDate) return 'today';
  if (thenDate === yesterday) return 'yesterday';

  return then.toLocaleDateString('en-US', {
    timeZone: APP_TIMEZONE,
    month: 'long',
    day: 'numeric',
  });
}
```

- [ ] **Step 2: Run the test; expect pass**

```bash
cd frontend && npm test -- --run dates.test.ts
```

Expected: 5/5 PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/dates.ts frontend/src/__tests__/dates.test.ts
git commit -m "feat(lib/dates): formatRelative for short CT-anchored relative times"
```

### Task 3.4: Rewrite Feed.tsx

**Files:**
- Rewrite: `frontend/src/pages/Feed.tsx`

- [ ] **Step 1: Replace the file's contents with the post-stream version**

```typescript
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import Button from '@/components/ui/AppButton';
import Card from '@/components/ui/AppCard';
import EmptyState from '@/components/ui/EmptyState';
import PageHeader from '@/components/ui/PageHeader';
import { ApiError } from '@/api/client';
import { getFeed, type FeedPost } from '@/api/posts';
import { formatRelative } from '@/lib/dates';

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function MilestonePost({ post }: { post: FeedPost }) {
  return (
    <Card>
      <div className="flex items-baseline gap-3">
        <Link
          to={`/u/${encodeURIComponent(post.username)}`}
          className="font-medium hover:text-primary transition-colors"
        >
          @{post.username}
        </Link>
        <span className="text-muted-foreground">
          {post.body ?? 'hit a milestone'}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatRelative(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}

function RecapPost({ post }: { post: FeedPost }) {
  const top = post.details?.top ?? [];
  return (
    <Card className="bg-accent/10">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h3 className="font-display text-xl tracking-tight">
          Yesterday&rsquo;s top 3
        </h3>
        <span className="label-mono text-muted-foreground">
          {formatRelative(post.timestamp)}
        </span>
      </div>
      <ol className="space-y-2">
        {top.map((entry, i) => (
          <li
            key={entry.username}
            className="flex items-baseline gap-3"
          >
            <span className="label-mono w-6 shrink-0 text-muted-foreground">
              #{i + 1}
            </span>
            <Link
              to={`/u/${encodeURIComponent(entry.username)}`}
              className="font-medium hover:text-primary transition-colors flex-1 min-w-0 truncate"
            >
              @{entry.username}
            </Link>
            <span className="font-mono tabular-nums">
              {formatNumber(entry.total)}
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function GenericPost({ post }: { post: FeedPost }) {
  return (
    <Card>
      <div className="flex items-baseline gap-3">
        <Link
          to={`/u/${encodeURIComponent(post.username)}`}
          className="font-medium hover:text-primary transition-colors"
        >
          @{post.username}
        </Link>
        <span className="text-muted-foreground">
          {post.body ?? `posted (${post.type})`}
        </span>
        <span className="label-mono text-muted-foreground ml-auto">
          {formatRelative(post.timestamp)}
        </span>
      </div>
    </Card>
  );
}

function FeedSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <div className="flex items-baseline gap-3">
            <span className="h-3 w-20 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 flex-1 bg-muted/60 rounded animate-pulse" />
            <span className="h-3 w-12 bg-muted/60 rounded animate-pulse" />
          </div>
        </Card>
      ))}
    </div>
  );
}

function ErrorCard({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : 'Could not load the feed.';
  return (
    <Card className="border-destructive/40 bg-destructive/5">
      <p className="text-destructive text-sm">{message}</p>
      <Button variant="secondary" className="mt-3" onClick={onRetry}>
        Try again
      </Button>
    </Card>
  );
}

export default function Feed() {
  const query = useQuery({
    queryKey: ['posts', 'feed', 50],
    queryFn: () => getFeed(50),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Feed"
        description="Recent milestones and recaps."
      />

      {query.isPending ? (
        <FeedSkeleton />
      ) : query.isError ? (
        <ErrorCard error={query.error} onRetry={() => query.refetch()} />
      ) : query.data.posts.length === 0 ? (
        <Card>
          <EmptyState message="No posts yet. Start walking." />
        </Card>
      ) : (
        <div className="space-y-4">
          {query.data.posts.map((post) => {
            if (post.type === 'leaderboard_recap') {
              return <RecapPost key={post.id} post={post} />;
            }
            if (post.type === 'steps_milestone') {
              return <MilestonePost key={post.id} post={post} />;
            }
            return <GenericPost key={post.id} post={post} />;
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run typecheck — make sure imports resolve**

```bash
cd frontend && npm run typecheck
```

Expected: PASS (no errors).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Feed.tsx
git commit -m "feat(pages/Feed): rewrite as chronological post stream"
```

### Task 3.5: Feed.test.tsx — failing tests

**Files:**
- Rewrite: `frontend/src/__tests__/Feed.test.tsx`

- [ ] **Step 1: Replace the file's contents with the new stream tests**

```typescript
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Feed from '@/pages/Feed';

function renderFeed() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/feed']}>
        <Feed />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.clearAllMocks();
});

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('Feed page (post stream)', () => {
  it('renders milestone posts with username + body + relative time', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        posts: [
          {
            id: 1,
            user_id: 1,
            username: 'micah',
            type: 'steps_milestone',
            timestamp: new Date().toISOString(),
            details: { threshold: 5000, date: '2026-05-23' },
            body: 'hit 5,000 steps',
          },
        ],
      }),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText('hit 5,000 steps')).toBeInTheDocument();
    });
    const link = screen.getByRole('link', { name: '@micah' });
    expect(link).toHaveAttribute('href', '/u/micah');
  });

  it('renders a recap card with the top-3 list', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        posts: [
          {
            id: 7,
            user_id: 1,
            username: 'micah',
            type: 'leaderboard_recap',
            timestamp: new Date().toISOString(),
            details: {
              date: '2026-05-23',
              top: [
                { username: 'micah', total: 12000 },
                { username: 'angela', total: 9500 },
                { username: 'bob', total: 4200 },
              ],
            },
            body: "Yesterday's top 3",
          },
        ],
      }),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText(/Yesterday/i)).toBeInTheDocument();
    });
    expect(screen.getByText('12,000')).toBeInTheDocument();
    expect(screen.getByText('9,500')).toBeInTheDocument();
    expect(screen.getByText('4,200')).toBeInTheDocument();
    // Each ranked username is a link to its profile
    expect(
      screen.getByRole('link', { name: '@angela' }),
    ).toHaveAttribute('href', '/u/angela');
  });

  it('shows the empty state when no posts have been written', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ posts: [] }),
    );

    renderFeed();

    await waitFor(() => {
      expect(
        screen.getByText('No posts yet. Start walking.'),
      ).toBeInTheDocument();
    });
  });

  it('shows an error card with retry on failed fetch', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(new Response('boom', { status: 500 }));

    renderFeed();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Try again' }),
      ).toBeInTheDocument();
    });
  });

  it('renders milestone + recap together in a mixed feed', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        posts: [
          {
            id: 9,
            user_id: 1,
            username: 'micah',
            type: 'leaderboard_recap',
            timestamp: new Date().toISOString(),
            details: {
              date: '2026-05-23',
              top: [{ username: 'micah', total: 9000 }],
            },
            body: "Yesterday's top 3",
          },
          {
            id: 8,
            user_id: 2,
            username: 'angela',
            type: 'steps_milestone',
            timestamp: new Date().toISOString(),
            details: { threshold: 10000, date: '2026-05-23' },
            body: 'hit 10,000 steps',
          },
        ],
      }),
    );

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText('hit 10,000 steps')).toBeInTheDocument();
    });
    expect(screen.getByText(/Yesterday/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the Feed tests**

```bash
cd frontend && npm test -- --run Feed.test.tsx
```

Expected: 5/5 PASS.

- [ ] **Step 3: Run the full frontend suite**

```bash
cd frontend && npm test
```

Expected: all tests pass.

- [ ] **Step 4: Run build + typecheck**

```bash
cd frontend && npm run typecheck && npm run build
```

Expected: both clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/__tests__/Feed.test.tsx
git commit -m "test(Feed): cover milestone + recap + empty + error in the new stream"
```

### Task 3.6: Push + PR

- [ ] **Step 1: Push**

```bash
git push -u origin feat/feed-post-stream
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --title "feat(frontend): Feed rewrite as chronological post stream" --body "$(cat <<'EOF'
Third of three PRs in the feed-redesign slice (spec: docs/superpowers/specs/2026-05-24-feed-milestones-recap-design.md).

- New api/posts.ts client wrapper for GET /api/posts and GET /api/posts/users/:username.
- formatRelative(iso, now?) helper in lib/dates.ts — short CT-anchored relative times ("5m ago", "yesterday", "May 21").
- pages/Feed.tsx rewritten: header + chronological list. Type-specific renderers:
  - steps_milestone -> "@username hit N,NNN steps · 2h ago"
  - leaderboard_recap -> Card with top-3 ranked list
  - sleep/steps/workout -> generic fallback row
- 5 new Feed tests + 5 new dates tests.

After this merges: /feed shows the live milestone + recap posts that PRs #1 + #2 generate. /leaderboard remains unchanged.
EOF
)"
```

- [ ] **Step 3: Wait for CI + merge**

```bash
gh pr checks <PR#> --watch --interval 8
gh pr merge <PR#> --squash --delete-branch
```

- [ ] **Step 4: Verify live**

Visit `https://synzoia.vercel.app/feed`. Should render whatever posts have accumulated from PRs #1 + #2 (milestone posts from any step writes since #1 merged; recap posts from cron runs since #2 merged).

---

## Self-Review (run after the plan is fully written)

**Spec coverage:**

| Spec section | Plan task(s) |
|---|---|
| 2. Migration 0007 | Task 1.1 |
| 3. Milestone detection on step write | Task 1.4 (test), 1.5 (impl) |
| 4. Daily recap cron + vercel.json | Tasks 2.2 (test), 2.3 (svc), 2.4 (route), 2.5 (vercel.json) |
| 5. Frontend api/posts.ts + Feed rewrite | Tasks 3.1, 3.4 |
| 5. formatRelative helper | Tasks 3.2 (test), 3.3 (impl) |
| 6. Tests (backend + frontend) | Tasks 1.4, 2.2, 3.2, 3.5 |
| 7. Three-PR rollout | PRs 1, 2, 3 above |
| 8. Out-of-scope items | Not implemented (correct) |

**Placeholder scan:** no TBDs, no "implement later", no "similar to Task N" without code. Each step has the actual code or command needed.

**Type consistency:** `MILESTONE_THRESHOLDS`, `detect_and_insert_milestone(conn, user_id, timestamp)`, `write_daily_recap(conn, today)`, `_today_ct()`, `_verify_cron_secret(authorization)`, `getFeed(limit?)`, `formatRelative(iso, now?)` — all names match between definitions and call sites across tasks.

**Scope check:** Three PRs map to three distinct subsystems but they share one spec because they're tightly coupled (the schema enables both server-side write paths and frontend rendering). Each PR is independently mergeable; (3) renders empty until (1) and (2) write data, but no breakage.
