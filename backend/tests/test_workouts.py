"""HTTP-level tests for POST /api/workouts/run + /api/workouts/calories.

Replaces the old single-row /workouts tests (which modeled calories
as a workout kind — wrong per Angela's design review). New shape:

  /run       → store run events; merge sub-3-min gaps; pace guard
               at [4, 13] mph; status provisional/final by captured-
               vs-ended; calories prorated from existing buckets.

  /calories  → store hourly active-energy buckets; re-prorate any of
               the user's runs that overlap the new bucket range.

Coverage:
  - Auth (Bearer required for both endpoints)
  - Happy path: one run lands with pace, status, calories_unavailable
  - Merge: two contiguous runs (<3 min gap) collapse into one row
  - No merge: two runs with >3 min gap stay independent
  - Pace guard: <4 mph walk and >13 mph "run" both dropped
  - Calories first, then run → run's calories populated immediately
  - Run first, then calories → calorie ingest re-prorates the run
  - Proration math: 30-min run spanning two hourly buckets sums correctly
  - Bucket re-post (same hour_start) updates in place
  - calories_unavailable flag flips true→false when buckets arrive
  - Provisional vs final by captured_at vs ended_at gap
  - Anti-spoofing: user_id in body is ignored
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main
from backend.app.schemas.workouts import (
    CalorieBucketEntry,
    IngestCaloriesRequest,
    IngestRunsRequest,
    RunEntry,
)
from backend.app.services import workouts as svc


ALICE_TOKEN = "ALCE-AAAA-AAAA-AAAA"
BOB_TOKEN = "BOBB-BBBB-BBBB-BBBB"


# ----- In-memory DB harness ----------------------------------------------


def _engine_with_users():
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
        # Post-0010 shape: separate `runs` and `calorie_buckets` tables.
        conn.execute(
            text(
                "CREATE TABLE runs ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "started_at text not null, "
                "ended_at text not null, "
                "duration_min integer not null, "
                "distance_m integer not null, "
                "pace_mph real not null, "
                "calories integer, "
                "calories_unavailable integer not null default 0, "
                "avg_heart_rate integer, "
                "max_heart_rate integer, "
                "status text not null, "
                "captured_at text not null default (datetime('now')), "
                "created_at text not null default (datetime('now')), "
                "UNIQUE (user_id, started_at))"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE calorie_buckets ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "hour_start text not null, "
                "hour_end text not null, "
                "kcal integer not null, "
                "captured_at text not null default (datetime('now')), "
                "created_at text not null default (datetime('now')), "
                "UNIQUE (user_id, hour_start))"
            )
        )
        conn.execute(
            text(
                "INSERT INTO profiles (username, token, join_date) "
                "VALUES (:u, :t, :j)"
            ),
            [
                {"u": "alice", "t": ALICE_TOKEN, "j": "2026-05-01T00:00:00"},
                {"u": "bob", "t": BOB_TOKEN, "j": "2026-05-01T00:00:00"},
            ],
        )
    return engine


def _count(engine, table: str, user_id: int | None = None) -> int:
    sql = f"SELECT count(*) FROM {table}"
    params: dict = {}
    if user_id is not None:
        sql += " WHERE user_id = :uid"
        params["uid"] = user_id
    with engine.connect() as conn:
        return int(conn.execute(text(sql), params).scalar() or 0)


def _select_run(engine, run_id: int) -> dict:
    with engine.connect() as conn:
        row = (
            conn.execute(
                text(
                    "SELECT calories, calories_unavailable, status, pace_mph "
                    "FROM runs WHERE id = :id"
                ),
                {"id": run_id},
            )
            .mappings()
            .one()
        )
        return dict(row)


# ----- Sample payloads ---------------------------------------------------


def _run_payload(**overrides) -> dict:
    """5 km in 30 min → 6.21 mph, comfortably inside the pace guard."""
    base = {
        "started_at": "2026-05-25T07:00:00",
        "ended_at": "2026-05-25T07:30:00",
        "distance_m": 5000,
        "avg_heart_rate": 145,
        "max_heart_rate": 172,
    }
    base.update(overrides)
    return base


def _runs_request(*runs: dict) -> dict:
    if not runs:
        runs = (_run_payload(),)
    return {"runs": list(runs)}


def _bucket(start_iso: str, end_iso: str, kcal: int) -> dict:
    return {"hour_start": start_iso, "hour_end": end_iso, "kcal": kcal}


# ----- Auth --------------------------------------------------------------


def test_run_without_auth_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    r = TestClient(main.app).post("/api/workouts/run", json=_runs_request())

    assert r.status_code == 401
    assert _count(engine, "runs") == 0


def test_calories_without_auth_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    r = TestClient(main.app).post(
        "/api/workouts/calories",
        json={"buckets": [_bucket("2026-05-25T07:00:00", "2026-05-25T08:00:00", 60)]},
    )

    assert r.status_code == 401
    assert _count(engine, "calorie_buckets") == 0


# ----- Run happy path ----------------------------------------------------


def test_single_run_stored_with_pace_and_calories_unavailable(monkeypatch):
    """One run, no calorie buckets in the DB yet — should land with
    calories=null + calories_unavailable=true so the UI knows to show
    '—' instead of 0 kcal."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=_runs_request(),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["dropped"] == 0
    assert body["merged_pairs"] == 0
    assert len(body["runs"]) == 1
    run = body["runs"][0]
    assert run["user_id"] == 1
    assert run["distance_m"] == 5000
    assert run["duration_min"] == 30
    # 5000m / 1609.344 = 3.107 mi over 0.5h → 6.21 mph
    assert abs(run["pace_mph"] - 6.21) < 0.05
    assert run["calories"] is None
    assert run["calories_unavailable"] is True
    assert _count(engine, "runs", user_id=1) == 1


# ----- Merge contiguous --------------------------------------------------


def test_two_contiguous_runs_merge_into_one_row(monkeypatch):
    """Strava-autopause case: run pauses at 7:15 and resumes at
    7:17 (2-min gap, sub-3-min). The two records should collapse
    into a single run row with summed distance + union window."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    leg1 = _run_payload(
        started_at="2026-05-25T07:00:00",
        ended_at="2026-05-25T07:15:00",
        distance_m=2500,
    )
    leg2 = _run_payload(
        started_at="2026-05-25T07:17:00",
        ended_at="2026-05-25T07:32:00",
        distance_m=2500,
    )

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=_runs_request(leg1, leg2),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["merged_pairs"] == 1
    assert body["dropped"] == 0
    assert len(body["runs"]) == 1
    run = body["runs"][0]
    assert run["distance_m"] == 5000
    assert run["started_at"].startswith("2026-05-25T07:00:00")
    assert run["ended_at"].startswith("2026-05-25T07:32:00")
    # 5000m / 1609.344 = 3.107 mi over 32 min = 0.533h → 5.83 mph
    assert abs(run["pace_mph"] - 5.83) < 0.05
    assert _count(engine, "runs", user_id=1) == 1


def test_runs_with_gap_over_3min_stay_separate(monkeypatch):
    """5-min gap between two runs → they are distinct activities and
    each get their own row."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    leg1 = _run_payload(
        started_at="2026-05-25T07:00:00",
        ended_at="2026-05-25T07:15:00",
        distance_m=2500,
    )
    leg2 = _run_payload(
        started_at="2026-05-25T07:20:00",
        ended_at="2026-05-25T07:35:00",
        distance_m=2500,
    )

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=_runs_request(leg1, leg2),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["merged_pairs"] == 0
    assert len(body["runs"]) == 2
    assert _count(engine, "runs", user_id=1) == 2


# ----- Pace guard --------------------------------------------------------


def test_run_below_4mph_is_dropped(monkeypatch):
    """A 'run' at 2.5 mph is a walk misclassified by the watch."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # 2 km in 30 min → 2.49 mph, below the 4mph floor.
    payload = _run_payload(
        started_at="2026-05-25T07:00:00",
        ended_at="2026-05-25T07:30:00",
        distance_m=2000,
    )

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=_runs_request(payload),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201
    body = r.json()
    assert body["dropped"] == 1
    assert body["runs"] == []
    assert _count(engine, "runs") == 0


def test_run_above_13mph_is_dropped(monkeypatch):
    """A 'run' at 25 mph is a bike/GPS glitch."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # 10 km in 15 min → 24.85 mph, above the 13mph ceiling.
    payload = _run_payload(
        started_at="2026-05-25T07:00:00",
        ended_at="2026-05-25T07:15:00",
        distance_m=10000,
    )

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=_runs_request(payload),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201
    body = r.json()
    assert body["dropped"] == 1
    assert body["runs"] == []


# ----- Calorie bucket ingest --------------------------------------------


def test_calorie_buckets_stored(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = {
        "buckets": [
            _bucket("2026-05-25T07:00:00", "2026-05-25T08:00:00", 60),
            _bucket("2026-05-25T08:00:00", "2026-05-25T09:00:00", 45),
        ]
    }

    r = TestClient(main.app).post(
        "/api/workouts/calories",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201, r.json()
    body = r.json()
    assert len(body["buckets"]) == 2
    assert body["affected_runs"] == []  # no runs in DB yet
    assert _count(engine, "calorie_buckets", user_id=1) == 2


def test_reposting_same_hour_bucket_updates_in_place(monkeypatch):
    """Apple Health can revise an hour's bucket as more samples
    arrive within the hour — re-post should update, not duplicate."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    client.post(
        "/api/workouts/calories",
        json={"buckets": [_bucket("2026-05-25T07:00:00", "2026-05-25T08:00:00", 60)]},
        headers=headers,
    )
    # Same hour_start, revised kcal.
    r2 = client.post(
        "/api/workouts/calories",
        json={"buckets": [_bucket("2026-05-25T07:00:00", "2026-05-25T08:00:00", 75)]},
        headers=headers,
    )

    assert r2.status_code == 201
    assert _count(engine, "calorie_buckets", user_id=1) == 1
    assert r2.json()["buckets"][0]["kcal"] == 75


# ----- Proration ---------------------------------------------------------


def test_run_then_calories_reprorates_run(monkeypatch):
    """Run ingest comes first (calories_unavailable=true). Calorie
    buckets arrive later → run's calories get populated and the flag
    flips to false. Run id appears in affected_runs."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    # 30-min run from 7:00 to 7:30.
    run_resp = client.post(
        "/api/workouts/run", json=_runs_request(), headers=headers
    )
    run_id = run_resp.json()["runs"][0]["id"]
    assert _select_run(engine, run_id)["calories_unavailable"] == 1
    assert _select_run(engine, run_id)["calories"] is None

    # Bucket 7-8 has 60 kcal. Run overlaps the bucket from 7:00-7:30 →
    # 30 of 60 minutes → 30 prorated kcal.
    cal_resp = client.post(
        "/api/workouts/calories",
        json={
            "buckets": [_bucket("2026-05-25T07:00:00", "2026-05-25T08:00:00", 60)]
        },
        headers=headers,
    )

    assert cal_resp.status_code == 201
    assert run_id in cal_resp.json()["affected_runs"]
    after = _select_run(engine, run_id)
    assert after["calories_unavailable"] == 0
    assert after["calories"] == 30


def test_calories_then_run_populates_at_write(monkeypatch):
    """Calorie buckets exist first. Run ingest reads them and stores
    prorated calories on the new row immediately."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    client.post(
        "/api/workouts/calories",
        json={
            "buckets": [_bucket("2026-05-25T07:00:00", "2026-05-25T08:00:00", 60)]
        },
        headers=headers,
    )
    run_resp = client.post(
        "/api/workouts/run", json=_runs_request(), headers=headers
    )

    assert run_resp.status_code == 201
    run = run_resp.json()["runs"][0]
    assert run["calories_unavailable"] is False
    assert run["calories"] == 30


def test_proration_across_two_buckets(monkeypatch):
    """Run spans two hourly buckets. Each contributes (overlap_min /
    bucket_span_min) * bucket_kcal. 7:45-8:15 (30 min total):
      bucket 7-8 (90 kcal):  overlap 7:45-8:00 = 15/60 * 90 = 22.5
      bucket 8-9 (120 kcal): overlap 8:00-8:15 = 15/60 * 120 = 30
      total = 52.5 → 52 or 53 depending on rounding (round-half-even
      gives 52)."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    client.post(
        "/api/workouts/calories",
        json={
            "buckets": [
                _bucket("2026-05-25T07:00:00", "2026-05-25T08:00:00", 90),
                _bucket("2026-05-25T08:00:00", "2026-05-25T09:00:00", 120),
            ]
        },
        headers=headers,
    )
    run_resp = client.post(
        "/api/workouts/run",
        json=_runs_request(
            _run_payload(
                started_at="2026-05-25T07:45:00",
                ended_at="2026-05-25T08:15:00",
                distance_m=4000,  # 30 min at ~5.0 mph, valid
            )
        ),
        headers=headers,
    )

    assert run_resp.status_code == 201
    run = run_resp.json()["runs"][0]
    assert run["calories_unavailable"] is False
    # Allow ±1 kcal for rounding mode differences.
    assert abs(run["calories"] - 53) <= 1


def test_bucket_not_overlapping_run_leaves_calories_null(monkeypatch):
    """A bucket far from the run window shouldn't touch the run."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    # Run 7:00-7:30.
    run_resp = client.post(
        "/api/workouts/run", json=_runs_request(), headers=headers
    )
    run_id = run_resp.json()["runs"][0]["id"]

    # Bucket 14:00-15:00 — nowhere near the run.
    cal_resp = client.post(
        "/api/workouts/calories",
        json={
            "buckets": [_bucket("2026-05-25T14:00:00", "2026-05-25T15:00:00", 60)]
        },
        headers=headers,
    )

    assert cal_resp.status_code == 201
    assert cal_resp.json()["affected_runs"] == []
    after = _select_run(engine, run_id)
    assert after["calories_unavailable"] == 1
    assert after["calories"] is None


# ----- Provisional vs final ---------------------------------------------


def test_status_provisional_when_captured_within_30min_of_end():
    """Direct service-level test so we can control capture_dt
    precisely without messing with system time."""
    started = datetime(2026, 5, 25, 7, 0, 0)
    ended = datetime(2026, 5, 25, 7, 30, 0)
    capture_recent = ended + timedelta(minutes=10)
    capture_late = ended + timedelta(minutes=45)

    assert svc._status_for(capture_recent, ended) == "provisional"
    assert svc._status_for(capture_late, ended) == "final"


def test_re_ingesting_a_provisional_run_finalizes_it(monkeypatch):
    """A run captured live (provisional) should flip to 'final' on a
    later re-post once the ended_at is well in the past."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # First ingest: capture is "now"-ish relative to ended_at → provisional.
    run = RunEntry(
        started_at=datetime(2026, 5, 25, 7, 0, 0),
        ended_at=datetime(2026, 5, 25, 7, 30, 0),
        distance_m=5000,
    )
    with engine.begin() as conn:
        first = svc.ingest_runs(
            conn,
            user_id=1,
            entries=[run],
            capture_dt=datetime(2026, 5, 25, 7, 40, 0),  # 10 min after end
        )
    assert first.runs[0].status == "provisional"

    # Second ingest, same window, captured 2 hours later → final.
    with engine.begin() as conn:
        second = svc.ingest_runs(
            conn,
            user_id=1,
            entries=[run],
            capture_dt=datetime(2026, 5, 25, 9, 30, 0),
        )
    assert second.runs[0].id == first.runs[0].id  # same row
    assert second.runs[0].status == "final"
    assert _count(engine, "runs", user_id=1) == 1


# ----- Anti-spoofing -----------------------------------------------------


def test_user_id_in_run_body_is_ignored(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = _runs_request()
    payload["user_id"] = 999  # outer-level shenanigans — Pydantic drops it
    payload["runs"][0]["user_id"] = 999

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    # Outer extra=forbid → 422; user can't sneak in unknown top-level keys.
    assert r.status_code == 422
    assert _count(engine, "runs") == 0


def test_run_only_creates_for_authenticated_user(monkeypatch):
    """Alice's POST creates a run under Alice's user_id; Bob's profile
    is unaffected even though both share the table."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    r = TestClient(main.app).post(
        "/api/workouts/run",
        json=_runs_request(),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert r.status_code == 201
    assert r.json()["runs"][0]["user_id"] == 1
    assert _count(engine, "runs", user_id=1) == 1
    assert _count(engine, "runs", user_id=2) == 0


# ----- Service-level pace-guard unit tests ------------------------------


def test_merge_consecutive_collapses_three_legs():
    """A 3-leg run with all gaps <3 min merges down to one."""
    entries = [
        RunEntry(
            started_at=datetime(2026, 5, 25, 7, 0),
            ended_at=datetime(2026, 5, 25, 7, 10),
            distance_m=1500,
        ),
        RunEntry(
            started_at=datetime(2026, 5, 25, 7, 11),
            ended_at=datetime(2026, 5, 25, 7, 20),
            distance_m=1500,
        ),
        RunEntry(
            started_at=datetime(2026, 5, 25, 7, 22),
            ended_at=datetime(2026, 5, 25, 7, 32),
            distance_m=1500,
        ),
    ]
    merged, pairs = svc._merge_consecutive(entries)

    assert pairs == 2  # leg1+leg2, then merged+leg3
    assert len(merged) == 1
    assert merged[0].distance_m == 4500
    assert merged[0].started_at == datetime(2026, 5, 25, 7, 0)
    assert merged[0].ended_at == datetime(2026, 5, 25, 7, 32)
