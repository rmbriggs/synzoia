# 30-Day Capped-Score Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all-time-total ranking with a rolling 30-day sum of per-day-capped values (steps + sleep), surfaced on the profile (3-card strip: 30-day score · Rank · Best) and the leaderboard (30-day board + Today tab).

**Architecture:** A shared `cap_and_sum` reduces existing per-(user,day) rows to a capped 30-day score per user; each service ranks by it. `get_user_summary` returns the user's `rank` + `score`; a new `/ranking` endpoint returns the global board. Frontend reads the new summary fields and points the leaderboard's main board at `/ranking`.

**Tech Stack:** FastAPI + SQLAlchemy + pytest; React + @tanstack/react-query + Vitest.

**Caps (module constants):** `STEPS_DAILY_CAP = 20_000`, `SLEEP_DAILY_CAP_MIN = 540` (9h). **Windows:** steps `[today-29, today]`; sleep `[today-30, today-1]` (ends last night).

---

## Setup

- [ ] **Step 0:** Backend tests run (`cd backend && python -m pytest -q | tail -3`); frontend `node_modules` symlink exists (`cd frontend && [ -e node_modules ] || ln -s /Users/micahbriggs/Developer/synzoia/frontend/node_modules ./node_modules`). All paths below are under `/Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows`.

---

### Task 1: `cap_and_sum` shared helper

**Files:** Modify `backend/app/services/windows.py`; Test `backend/tests/test_windows.py`

- [ ] **Step 1: Failing test** — append to `backend/tests/test_windows.py`:
```python
from datetime import date
from backend.app.services.windows import cap_and_sum


def test_cap_and_sum_caps_each_day_then_sums_per_user():
    rows = [
        (1, date(2026, 6, 1), 8000),
        (1, date(2026, 6, 2), 30000),   # capped to 20000
        (2, date(2026, 6, 1), 12000),
    ]
    assert cap_and_sum(rows, 20000) == {1: 28000, 2: 12000}


def test_cap_and_sum_empty():
    assert cap_and_sum([], 20000) == {}
```

- [ ] **Step 2: Run, expect FAIL** — `cd backend && python -m pytest tests/test_windows.py -q -k cap_and_sum` (ImportError: cap_and_sum).

- [ ] **Step 3: Implement** — add to `backend/app/services/windows.py`:
```python
from collections import defaultdict


def cap_and_sum(
    rows: "list[tuple[int, object, int]]", cap: int
) -> dict[int, int]:
    """Reduce per-(user, day, value) rows to a per-user score: each day's
    value is capped at `cap` (so one monster day can't carry a user), then
    summed. Used for the 30-day capped ranking."""
    scores: dict[int, int] = defaultdict(int)
    for user_id, _day, value in rows:
        scores[int(user_id)] += min(int(value), cap)
    return dict(scores)
```

- [ ] **Step 4: Run, expect PASS** — `cd backend && python -m pytest tests/test_windows.py -q`.

- [ ] **Step 5: Commit**
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add backend/app/services/windows.py backend/tests/test_windows.py
git commit -m "feat(backend): add cap_and_sum (per-day-capped per-user score)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Steps ranking (score + global ranking + summary)

**Files:** Modify `backend/app/services/steps.py`; Test `backend/tests/test_steps_service.py`

Reference: `_daily_totals_in_range(conn, start, end) -> list[(uid, day, total)]`, `_usernames_for`, `_build_leaderboard(totals_by_user, usernames)`, `_rank_of_user(totals_by_user, uid)`, `rolling_bounds` already exist.

- [ ] **Step 1: Failing tests** — add to `backend/tests/test_steps_service.py` (reuse the file's engine/insert fixture):
```python
def test_global_ranking_caps_days_and_ranks_by_30d_score(seeded_conn):
    from datetime import date, timedelta
    from backend.app.services import steps as svc
    as_of = date(2026, 6, 2)
    # amy: two normal days inside window
    _insert_steps(seeded_conn, "amy", as_of - timedelta(days=1), 9000)
    _insert_steps(seeded_conn, "amy", as_of - timedelta(days=2), 9000)
    # bob: one monster day (capped to 20000) -> loses to amy's 18000? no, 20000>18000
    _insert_steps(seeded_conn, "bob", as_of - timedelta(days=1), 50000)
    resp = svc.get_global_ranking(seeded_conn, as_of)
    by_user = {e.username: (e.rank, e.total) for e in resp.leaderboard}
    assert by_user["bob"][1] == 20000   # 50000 capped to 20000
    assert by_user["amy"][1] == 18000
    assert by_user["bob"][0] == 1 and by_user["amy"][0] == 2


def test_user_summary_returns_30d_rank_and_score(seeded_conn):
    from datetime import date, timedelta
    from backend.app.services import steps as svc
    as_of = date(2026, 6, 2)
    _insert_steps(seeded_conn, "amy", as_of - timedelta(days=1), 9000)
    _insert_steps(seeded_conn, "amy", as_of - timedelta(days=40), 99999)  # outside 30d
    resp = svc.get_user_summary(seeded_conn, "amy", as_of)
    assert resp.score == 9000           # day 40 excluded
    assert resp.rank == 1
```

- [ ] **Step 2: Run, expect FAIL** — `cd backend && python -m pytest tests/test_steps_service.py -q -k "ranking or 30d"` (get_global_ranking missing; get_user_summary has no as_of/score/rank).

- [ ] **Step 3: Implement** in `backend/app/services/steps.py`:

(a) Add the cap constant near the top constants and the import:
```python
from backend.app.services.windows import rolling_bounds, cap_and_sum

STEPS_DAILY_CAP = 20_000
```

(b) Add a global ranking function (place near `get_global_weekly`):
```python
def get_global_ranking(conn: Connection, as_of: date) -> GlobalWeeklyResponse:
    """Global board ranked by the 30-day capped score (sum of per-CT-day
    totals, each capped at STEPS_DAILY_CAP, over [as_of-29, as_of])."""
    start, end = rolling_bounds(as_of, 30)
    rows = _daily_totals_in_range(conn, start, end)
    scores = cap_and_sum(rows, STEPS_DAILY_CAP)
    usernames = _usernames_for(conn, scores.keys())
    leaderboard = _build_leaderboard(scores, usernames)
    return GlobalWeeklyResponse(
        week_start=start,
        week_end=end,
        total_steps=sum(scores.values()),
        leaderboard=leaderboard,
        daily_breakdown=[],
    )
```
(Reuses `GlobalWeeklyResponse`; `daily_breakdown` empty — the ranking board shows standings, not bars. `total_steps` field carries the summed score.)

(c) Change `get_user_summary` signature + add rank/score from the 30-day window. Replace the all-time `rank_all_time` computation:
```python
def get_user_summary(
    conn: Connection, username: str, as_of: date
) -> UserSummaryResponse:
    user_id, join_date = _lookup_user(conn, username)

    # All-time best day (unchanged): walk every (user, CT day) max.
    daily_max = _all_time_daily_max(conn)
    user_days = [
        (d, t) for (uid, d), t in daily_max.items() if uid == user_id
    ]
    best_day: UserBestDay | None = None
    if user_days:
        best_d, best_t = max(user_days, key=lambda x: x[1])
        best_day = UserBestDay(date=best_d, total=best_t)

    # 30-day capped score + rank.
    start, end = rolling_bounds(as_of, 30)
    scores = cap_and_sum(_daily_totals_in_range(conn, start, end), STEPS_DAILY_CAP)
    score = scores.get(user_id, 0)
    rank = _rank_of_user(scores, user_id)

    return UserSummaryResponse(
        username=username,
        join_date=join_date,
        score=score,
        best_day=best_day,
        rank=rank,
    )
```
(Drops `total_steps_all_time` and `days_active` from the response — they're no longer shown. See Task 4 for the schema change.)

- [ ] **Step 4: Run, expect PASS** — `cd backend && python -m pytest tests/test_steps_service.py -q`. Fix existing summary tests that referenced `total_steps_all_time` / `days_active` / `rank_all_time` (update to `score` / `rank`, pass `as_of`).

- [ ] **Step 5: Commit**
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add backend/app/services/steps.py backend/tests/test_steps_service.py
git commit -m "feat(backend): steps 30-day capped ranking + summary rank/score

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Sleep ranking (mirror of Task 2)

**Files:** Modify `backend/app/services/sleep.py`; Test `backend/tests/test_sleep_service.py`

Reference: sleep's `_nightly_rows_in_range(conn, start, end) -> list[(uid, night_of, duration_min)]`, `_usernames_for`, `_build_leaderboard`, `_rank_of_user`, `rolling_bounds` exist. Window ends **last night** = `as_of` passed by caller as today−1.

- [ ] **Step 1: Failing tests** — add to `backend/tests/test_sleep_service.py`:
```python
def test_sleep_global_ranking_caps_and_ranks(seeded_conn):
    from datetime import date, timedelta
    from backend.app.services import sleep as svc
    as_of = date(2026, 6, 1)  # = last night relative to 2026-06-02
    _insert_sleep(seeded_conn, "amy", night_of=as_of, duration_min=420)
    _insert_sleep(seeded_conn, "bob", night_of=as_of, duration_min=900)  # capped 540
    resp = svc.get_global_ranking(seeded_conn, as_of)
    by_user = {e.username: (e.rank, e.total) for e in resp.leaderboard}
    assert by_user["bob"][1] == 540   # 900 capped
    assert by_user["amy"][1] == 420


def test_sleep_user_summary_rank_and_score(seeded_conn):
    from datetime import date, timedelta
    from backend.app.services import sleep as svc
    as_of = date(2026, 6, 1)
    _insert_sleep(seeded_conn, "amy", night_of=as_of, duration_min=430)
    _insert_sleep(seeded_conn, "amy", night_of=as_of - timedelta(days=40), duration_min=480)
    resp = svc.get_user_summary(seeded_conn, "amy", as_of)
    assert resp.score == 430   # 40-nights-ago excluded
    assert resp.rank == 1
```

- [ ] **Step 2: Run, expect FAIL** — `cd backend && python -m pytest tests/test_sleep_service.py -q -k "ranking or summary_rank"`.

- [ ] **Step 3: Implement** in `backend/app/services/sleep.py` (mirror Task 2):
(a) `from backend.app.services.windows import rolling_bounds, cap_and_sum` (add `cap_and_sum`); `SLEEP_DAILY_CAP_MIN = 540`.
(b) `get_global_ranking(conn, as_of)`:
```python
def get_global_ranking(conn: Connection, as_of: date) -> GlobalWeeklyResponse:
    start, end = rolling_bounds(as_of, 30)
    rows = _nightly_rows_in_range(conn, start, end)
    scores = cap_and_sum(rows, SLEEP_DAILY_CAP_MIN)
    usernames = _usernames_for(conn, scores.keys())
    leaderboard = _build_leaderboard(scores, usernames)
    return GlobalWeeklyResponse(
        week_start=start, week_end=end,
        total_minutes=sum(scores.values()),
        leaderboard=leaderboard, daily_breakdown=[],
    )
```
(Match sleep's `GlobalWeeklyResponse` field name for the total — read the sleep schema; it may be `total_minutes` or similar. Use whatever the existing sleep global weekly response uses.)
(c) `get_user_summary(conn, username, as_of)`: keep the all-time `best_night`; compute `score`/`rank` from `cap_and_sum(_nightly_rows_in_range(conn, *rolling_bounds(as_of, 30)), SLEEP_DAILY_CAP_MIN)`. Return `score` + `rank` (drop `total_minutes_all_time`, `nights_logged`).

- [ ] **Step 4: Run, expect PASS** — `cd backend && python -m pytest tests/test_sleep_service.py -q`. Fix existing sleep summary tests referencing the dropped fields.

- [ ] **Step 5: Commit**
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add backend/app/services/sleep.py backend/tests/test_sleep_service.py
git commit -m "feat(backend): sleep 30-day capped ranking + summary rank/score

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Schemas + routes (`/ranking`, summary `as_of`)

**Files:** Modify `backend/app/schemas/steps.py`, `backend/app/schemas/sleep.py`, `backend/app/routes/steps.py`, `backend/app/routes/sleep.py`; Test `backend/tests/test_steps_routes.py`, `backend/tests/test_sleep_routes.py`

- [ ] **Step 1: Failing tests** — add to `backend/tests/test_steps_routes.py`:
```python
def test_ranking_route_returns_30d_capped_board(client_with_amy):
    resp = client_with_amy.get("/api/steps/ranking?as_of=2026-06-02")
    assert resp.status_code == 200
    body = resp.json()
    assert "leaderboard" in body and isinstance(body["leaderboard"], list)


def test_user_summary_route_has_rank_and_score(client_with_amy):
    resp = client_with_amy.get("/api/steps/users/amy/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "score" in body and "rank" in body
    assert "total_steps_all_time" not in body and "days_active" not in body
```

- [ ] **Step 2: Run, expect FAIL** — `cd backend && python -m pytest tests/test_steps_routes.py -q -k "ranking or rank_and_score"`.

- [ ] **Step 3: Implement**

(a) `backend/app/schemas/steps.py` — change `UserSummaryResponse`:
```python
class UserSummaryResponse(BaseModel):
    username: str
    join_date: datetime
    score: int            # 30-day capped score (the ranking metric)
    best_day: Optional[UserBestDay] = None
    rank: Optional[int] = None
```
(Remove `total_steps_all_time`, `days_active`, `rank_all_time`.)

(b) `backend/app/schemas/sleep.py` — same shape for the sleep summary: `score: int`, `best_night`, `rank: Optional[int]` (remove `total_minutes_all_time`, `nights_logged`, `rank_all_time`).

(c) `backend/app/routes/steps.py` — summary route passes `as_of=_today()`; add ranking route:
```python
@router.get("/summary", ...)  # the per-user one
def user_summary(username: str) -> UserSummaryResponse:
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_summary(conn, username, _today())
    except svc.UserNotFound as e:
        raise _user_not_found(e.username) from e


@router.get("/ranking", response_model=GlobalWeeklyResponse)
def global_ranking(as_of: Optional[date] = Query(default=None)) -> GlobalWeeklyResponse:
    with db.get_engine().connect() as conn:
        return svc.get_global_ranking(conn, as_of or _today())
```

(d) `backend/app/routes/sleep.py` — same, but the summary + ranking anchor to **last night**:
```python
def user_summary(username: str) -> UserSummaryResponse:
    try:
        with db.get_engine().connect() as conn:
            return svc.get_user_summary(conn, username, _today() - timedelta(days=1))
    ...

@router.get("/ranking", response_model=GlobalWeeklyResponse)
def global_ranking(as_of: Optional[date] = Query(default=None)) -> GlobalWeeklyResponse:
    with db.get_engine().connect() as conn:
        return svc.get_global_ranking(conn, as_of or (_today() - timedelta(days=1)))
```
(Ensure `from datetime import timedelta` is imported in sleep.py routes.)

- [ ] **Step 4: Run, expect PASS** — `cd backend && python -m pytest -q`. Update any route/summary tests asserting old fields; the whole backend suite green (modulo the pre-existing `test_db.py::test_engine_uses_null_pool` psycopg failure).

- [ ] **Step 5: Commit**
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add backend/app/schemas/steps.py backend/app/schemas/sleep.py backend/app/routes/steps.py backend/app/routes/sleep.py backend/tests/test_steps_routes.py backend/tests/test_sleep_routes.py
git commit -m "feat(backend): /ranking routes + summary rank/score schema + as_of

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Frontend API types + ranking fetcher

**Files:** Modify `frontend/src/api/steps.ts`, `frontend/src/api/sleep.ts`

- [ ] **Step 1:** Update `UserSummaryResponse` (steps.ts) to match the backend: replace `total_steps_all_time`/`days_active`/`rank_all_time` with `score: number` and `rank: number | null` (keep `best_day`, `username`, `join_date`). Do the same in sleep.ts (`score`, `rank`, keep `best_night`).
- [ ] **Step 2:** Add `getGlobalRanking(asOf?: string)` to `steps.ts` (and `sleep.ts` if needed later — leaderboard is steps-only so steps.ts is required):
```ts
export function getGlobalRanking(asOf?: string): Promise<GlobalWeeklyResponse> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : '';
  return apiFetch<GlobalWeeklyResponse>(`/steps/ranking${qs}`);
}
```
- [ ] **Step 3:** Typecheck will fail at Profile/Leaderboard call sites until Tasks 6–7 — that's expected; do not run a full typecheck yet. Commit:
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add frontend/src/api/steps.ts frontend/src/api/sleep.ts
git commit -m "feat(api): summary score/rank fields + getGlobalRanking

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Profile 3-card strip (30-day score · Rank · Best)

**Files:** Modify `frontend/src/pages/Profile.tsx`; Test `frontend/src/__tests__/Profile.test.tsx`

- [ ] **Step 1: Failing test** — update the summary-mock + assert the new strip. In `Profile.test.tsx`, change the steps/sleep `/summary` mocks to return `{ username, join_date, score, best_day|best_night, rank }` (drop old fields), and add/adjust a test:
```ts
it('renders the 3-card strip: 30-day score, rank, best', async () => {
  globalThis.fetch = routedMock(summaryMocks());
  renderAt('/u/alice');
  expect(await screen.findAllByText('30-day score')).toHaveLength(2); // steps + sleep
  expect(screen.getAllByText('Rank')).toHaveLength(2);
  expect(screen.queryByText('All-time steps')).not.toBeInTheDocument();
  expect(screen.queryByText('Days active')).not.toBeInTheDocument();
});
```
(Update `summaryMocks()`/`aliceSleepSummary`/`aliceSummary` accordingly — they currently return the old fields.)

- [ ] **Step 2: Run, expect FAIL** — `cd frontend && npm test -- --run src/__tests__/Profile.test.tsx`.

- [ ] **Step 3: Implement** — in `Profile.tsx`, `StatStrip` (steps) becomes three cards:
```tsx
function StatStrip({ data }: { data: UserSummaryResponse }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      <StatCard label="30-day score" value={formatNumber(data.score)} />
      <StatCard label="Rank" value={data.rank !== null ? `#${data.rank}` : '—'} />
      <StatCard
        label="Best day"
        value={data.best_day ? formatNumber(data.best_day.total) : '—'}
        sub={data.best_day ? formatJoinDate(data.best_day.date) : undefined}
      />
    </div>
  );
}
```
(Match the existing `StatCard` props/`sub` and the existing grid wrapper class — read the current StatStrip for the exact container + StatCard signature; drop the All-time-steps and Days-active cards.) Do the analogous edit to `SleepStatStrip`: `30-day score` (formatSleepHours(data.score)), `Rank`, `Best night`; drop All-time-sleep + Nights-logged.

- [ ] **Step 4: Run, expect PASS** — `cd frontend && npm test -- --run src/__tests__/Profile.test.tsx`.

- [ ] **Step 5: Commit**
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add frontend/src/pages/Profile.tsx frontend/src/__tests__/Profile.test.tsx
git commit -m "feat(profile): 3-card strip — 30-day score, rank, best (drop vanity cards)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Leaderboard main board → 30-day ranking

**Files:** Modify `frontend/src/pages/Leaderboard.tsx`; Test `frontend/src/__tests__/Leaderboard.test.tsx`

- [ ] **Step 1: Failing test** — assert the main board tab is the 30-day ranking and a Today tab exists. In `Leaderboard.test.tsx` (mock `getGlobalRanking`/`/ranking` + `/daily`):
```ts
it('ranks by the 30-day board and keeps a Today tab', async () => {
  // mock /ranking -> leaderboard list; /daily -> today
  renderLeaderboard();
  expect(await screen.findByText('Last 30 days')).toBeInTheDocument();
  expect(screen.getByText('Today')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run, expect FAIL** — `cd frontend && npm test -- --run src/__tests__/Leaderboard.test.tsx`.

- [ ] **Step 3: Implement** — in `Leaderboard.tsx`: change `TABS` to `[{key:'today',label:'Today'},{key:'ranking',label:'Last 30 days'}]`; rename `WeeklyPanel`→`RankingPanel` calling `getGlobalRanking(today)` with key `['steps','ranking', today]`; render `query.data.leaderboard` standings (drop the `WeeklyBars`/`daily_breakdown` chart — ranking has none; just the standings list + heading "Last 30 days"). Default tab → `ranking`. Keep `TodayPanel` unchanged. Update the `getGlobalWeekly` import → `getGlobalRanking`.

- [ ] **Step 4: Full check** — `cd frontend && npm test -- --run && npm run typecheck && npx eslint src/pages/Leaderboard.tsx src/pages/Profile.tsx src/api/steps.ts src/api/sleep.ts` (all green). Then `cd ../backend && python -m pytest -q` (green modulo the pre-existing psycopg failure).

- [ ] **Step 5: Commit**
```bash
cd /Users/micahbriggs/Developer/synzoia/.claude/worktrees/rolling-windows
git add frontend/src/pages/Leaderboard.tsx frontend/src/__tests__/Leaderboard.test.tsx
git commit -m "feat(leaderboard): main board is the 30-day capped ranking + Today tab

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:** metric/caps → Tasks 1–4 (`cap_and_sum` + `rolling_bounds(…,30)` + `STEPS_DAILY_CAP=20_000`/`SLEEP_DAILY_CAP_MIN=540`); steps window today, sleep window today−1 → Tasks 2/3 (service) + 4 (routes pass `_today()` / `_today()-1`); profile 3-card strip → Task 6; leaderboard 30-day board + Today tab → Task 7; rename `rank_all_time→rank` + add `score` → Tasks 2/3/4. ✓
- **Placeholder scan:** none — new code is complete; modifications give exact before→after or precise instructions to match existing signatures (StatCard props, sleep global-weekly total field name) by reading the file.
- **Type consistency:** `cap_and_sum(rows, cap)` used identically in Tasks 2/3. `get_global_ranking(conn, as_of)` and `get_user_summary(conn, username, as_of)` signatures consistent across service (2/3) and routes (4). Frontend `UserSummaryResponse` (`score`, `rank`) consistent across api types (5), Profile (6). `getGlobalRanking(asOf?)` consistent (5 → 7). Window: steps `as_of=today`, sleep `as_of=today-1` consistent service↔route.
- **Note for implementers:** sleep's global-weekly response total field and `StatCard`'s `sub` prop must be matched to the actual code (read the file) — flagged inline.
