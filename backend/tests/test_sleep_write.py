"""HTTP-level tests for POST /api/sleep — the new sessionization path.

Replaces the old hours-based test suite. The iOS Shortcut now sends
RAW HealthKit samples as five newline-joined strings plus a capture
timestamp; the backend parses, sessionizes, classifies, dedupes,
and returns an array of one or more session records.

Tests here cover:
- Auth (token required, missing/bad → 401)
- Happy path: the test-oracle night from the spec produces ~508 min
  asleep with Core/Deep/REM breakdown and a single wakeup.
- Sessionization: a night + a daytime nap arrive in the same payload
  and land as two separate sessions.
- Overlap dedup: re-posting the same window updates the existing row
  rather than creating a duplicate.
- Provisional → final transition: a payload captured mid-session is
  provisional; the same session captured >30 min after wake is final.
- Anti-spoofing: user_id in the body is ignored.
- Validation: mismatched array lengths → 422.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


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
        # Post-0009 sleep shape: BIGSERIAL id, full session columns,
        # no UNIQUE(user_id, night_of).
        conn.execute(
            text(
                "CREATE TABLE sleep ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "bedtime text not null, "
                "wake_time text not null, "
                "duration_min integer not null, "
                "rem_minutes integer, "
                "core_minutes integer, "
                "deep_minutes integer, "
                "awake_minutes integer, "
                "night_of text not null, "
                "session_type text not null default 'night', "
                "status text not null default 'final', "
                "review_flag integer not null default 0, "
                "captured_at text not null default (datetime('now')), "
                "onset_at text not null, "
                "sleep_date text not null, "
                "created_at text not null default (datetime('now')))"
            )
        )
        conn.execute(
            text(
                # Mirrors live schema post-migration 0011 — no
                # username column on posts; feed JOINs profiles to
                # resolve the writer's current name.
                "CREATE TABLE posts ("
                "id integer primary key autoincrement, "
                "user_id integer not null, "
                "type text not null, "
                "timestamp text not null, "
                "details text, "
                "body text)"
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


def _count_sleep(engine, user_id=None) -> int:
    with engine.connect() as conn:
        if user_id is None:
            return int(
                conn.execute(text("SELECT count(*) FROM sleep")).scalar() or 0
            )
        return int(
            conn.execute(
                text("SELECT count(*) FROM sleep WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar()
            or 0
        )


# ----- Sample payload (the test oracle from the spec) ---------------------


# May 25 2026 night: 12:07 AM → 8:52 AM, includes the awake gaps and
# stages from Angela's webhook capture. Used as the gold reference.
_NIGHT_VALUES = (
    "Deep\nCore\nAwake\nCore\nREM\nCore\nREM\nCore\nDeep\nCore\nDeep\nCore\n"
    "Awake\nCore\nREM\nCore\nDeep\nCore\nDeep\nCore\nREM\nCore\nAwake\nCore\n"
    "REM\nCore\nAwake\nCore\nREM\nCore\nAwake\nCore"
)
_NIGHT_STARTS = (
    "May 25, 2026 at 12:07 AM\nMay 25, 2026 at 12:21 AM\n"
    "May 25, 2026 at 12:29 AM\nMay 25, 2026 at 12:30 AM\n"
    "May 25, 2026 at 12:38 AM\nMay 25, 2026 at 12:42 AM\n"
    "May 25, 2026 at 1:40 AM\nMay 25, 2026 at 2:08 AM\n"
    "May 25, 2026 at 2:32 AM\nMay 25, 2026 at 2:40 AM\n"
    "May 25, 2026 at 3:02 AM\nMay 25, 2026 at 3:02 AM\n"
    "May 25, 2026 at 3:09 AM\nMay 25, 2026 at 3:11 AM\n"
    "May 25, 2026 at 3:17 AM\nMay 25, 2026 at 3:57 AM\n"
    "May 25, 2026 at 4:24 AM\nMay 25, 2026 at 4:25 AM\n"
    "May 25, 2026 at 4:31 AM\nMay 25, 2026 at 4:51 AM\n"
    "May 25, 2026 at 4:59 AM\nMay 25, 2026 at 5:29 AM\n"
    "May 25, 2026 at 6:06 AM\nMay 25, 2026 at 6:07 AM\n"
    "May 25, 2026 at 6:13 AM\nMay 25, 2026 at 6:43 AM\n"
    "May 25, 2026 at 7:28 AM\nMay 25, 2026 at 7:39 AM\n"
    "May 25, 2026 at 7:49 AM\nMay 25, 2026 at 8:23 AM\n"
    "May 25, 2026 at 8:36 AM\nMay 25, 2026 at 8:38 AM"
)
_NIGHT_ENDS = (
    "May 25, 2026 at 12:21 AM\nMay 25, 2026 at 12:29 AM\n"
    "May 25, 2026 at 12:30 AM\nMay 25, 2026 at 12:38 AM\n"
    "May 25, 2026 at 12:42 AM\nMay 25, 2026 at 1:40 AM\n"
    "May 25, 2026 at 2:08 AM\nMay 25, 2026 at 2:32 AM\n"
    "May 25, 2026 at 2:40 AM\nMay 25, 2026 at 3:02 AM\n"
    "May 25, 2026 at 3:02 AM\nMay 25, 2026 at 3:09 AM\n"
    "May 25, 2026 at 3:11 AM\nMay 25, 2026 at 3:17 AM\n"
    "May 25, 2026 at 3:57 AM\nMay 25, 2026 at 4:24 AM\n"
    "May 25, 2026 at 4:25 AM\nMay 25, 2026 at 4:31 AM\n"
    "May 25, 2026 at 4:51 AM\nMay 25, 2026 at 4:59 AM\n"
    "May 25, 2026 at 5:29 AM\nMay 25, 2026 at 6:06 AM\n"
    "May 25, 2026 at 6:07 AM\nMay 25, 2026 at 6:13 AM\n"
    "May 25, 2026 at 6:43 AM\nMay 25, 2026 at 7:28 AM\n"
    "May 25, 2026 at 7:39 AM\nMay 25, 2026 at 7:49 AM\n"
    "May 25, 2026 at 8:23 AM\nMay 25, 2026 at 8:36 AM\n"
    "May 25, 2026 at 8:38 AM\nMay 25, 2026 at 8:52 AM"
)
_NIGHT_TYPES = "\n".join(["Sleep"] * 32)
_NIGHT_DURATION = (
    "14:01\n8:00\n30\n8:30\n4:00\n57:35\n28:02\n24:32\n7:30\n22:02\n30\n7:00\n"
    "2:00\n5:30\n40:33\n26:32\n1:30\n6:00\n19:31\n8:00\n30:02\n37:03\n30\n"
    "6:00\n30:32\n45:03\n10:30\n10:00\n34:33\n13:01\n1:30\n14:01"
)


def _night_payload(timestamp: str = "2026-05-26T09:00:00-04:00") -> dict:
    """The test-oracle night, captured by default at 9 AM the next day
    (so wake at 8:52 AM means the session is finalized, not provisional)."""
    return {
        "values": _NIGHT_VALUES,
        "starts": _NIGHT_STARTS,
        "ends": _NIGHT_ENDS,
        "types": _NIGHT_TYPES,
        "duration": _NIGHT_DURATION,
        "timestamp": timestamp,
    }


# ----- Auth tests ---------------------------------------------------------


def test_ingest_without_auth_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post("/api/sleep", json=_night_payload())

    assert response.status_code == 401
    assert _count_sleep(engine) == 0


def test_ingest_with_bad_token_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json=_night_payload(),
        headers={"Authorization": "Bearer not_a_real_token"},
    )

    assert response.status_code == 401
    assert _count_sleep(engine) == 0


# ----- Happy path: test-oracle night --------------------------------------


def test_ingest_night_payload_matches_oracle(monkeypatch):
    """The spec's golden values: total_asleep ≈ 508, Core ≈ 299,
    REM ≈ 166, Deep ≈ 43, awake ≈ 17, type=night, status=final.
    We allow ±1 minute slop because we truncate seconds → minutes."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json=_night_payload(),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    sessions = body["sessions"]
    assert len(sessions) == 1
    s = sessions[0]

    assert s["user_id"] == 1  # alice
    assert s["session_type"] == "night"
    assert s["status"] == "final"
    assert s["review_flag"] is False

    # Oracle: 508 min asleep (±1 for truncation)
    assert 506 <= s["total_asleep_min"] <= 510, s["total_asleep_min"]
    # Per-stage (±1)
    assert 297 <= s["core_min"] <= 301, s["core_min"]
    assert 164 <= s["rem_min"] <= 168, s["rem_min"]
    assert 41 <= s["deep_min"] <= 45, s["deep_min"]
    # Awake total ≈ 17 min
    assert 15 <= s["awake_min"] <= 19, s["awake_min"]
    # One wakeup at the 5-min threshold (the 57:35 Awake run)
    assert s["wakeups"] == 1
    # Efficiency ~97%
    assert 0.94 <= s["efficiency"] <= 1.0
    # Stored as one row
    assert _count_sleep(engine, user_id=1) == 1


# ----- Sessionization: night + nap ----------------------------------------


def test_ingest_night_and_nap_stores_both_returns_latest(monkeypatch):
    """One night (00:00-08:00) + an afternoon nap (14:00-14:45) in the
    same payload should land as TWO rows in the DB. The response only
    returns the LATEST session by wake time (the nap here) — Apple
    Health's calendar-day filter routinely pulls multi-session
    payloads, and the client only wants the most recent for its
    just-woke-up UI flow."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = {
        "values": "Core\nDeep\nCore\nCore\nDeep",
        "starts": (
            "May 25, 2026 at 12:00 AM\n"  # night begins
            "May 25, 2026 at 4:00 AM\n"
            "May 25, 2026 at 7:00 AM\n"
            "May 25, 2026 at 2:00 PM\n"  # nap begins (8h gap)
            "May 25, 2026 at 2:20 PM"
        ),
        "ends": (
            "May 25, 2026 at 4:00 AM\n"
            "May 25, 2026 at 7:00 AM\n"
            "May 25, 2026 at 8:00 AM\n"
            "May 25, 2026 at 2:20 PM\n"
            "May 25, 2026 at 2:45 PM"
        ),
        "types": "Sleep\nSleep\nSleep\nSleep\nSleep",
        "duration": "240:00\n180:00\n60:00\n20:00\n25:00",
        "timestamp": "2026-05-25T18:00:00-04:00",
    }

    response = TestClient(main.app).post(
        "/api/sleep",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201, response.json()
    sessions = response.json()["sessions"]
    # Response: only the latest (nap, wake 2:45 PM > night wake 8:00 AM)
    assert len(sessions) == 1
    assert sessions[0]["session_type"] == "nap"
    # DB: both rows persisted, queryable via GET endpoints
    assert _count_sleep(engine, user_id=1) == 2


# ----- Overlap dedup ------------------------------------------------------


def test_reposting_same_window_updates_existing_row(monkeypatch):
    """The Shortcut polls every 30 min and sends overlapping windows.
    Two POSTs of the SAME night must result in ONE row, not two."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    first = client.post("/api/sleep", json=_night_payload(), headers=headers)
    assert first.status_code == 201
    assert _count_sleep(engine, user_id=1) == 1

    second = client.post("/api/sleep", json=_night_payload(), headers=headers)
    assert second.status_code == 201
    assert _count_sleep(engine, user_id=1) == 1  # still one row


# ----- Provisional → final ------------------------------------------------


def test_mid_session_capture_is_provisional(monkeypatch):
    """If the payload is captured within 30 min of the last sample end,
    the session is provisional."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # Capture at 9:00 AM, just 8 min after the 8:52 AM wake — provisional.
    response = TestClient(main.app).post(
        "/api/sleep",
        json=_night_payload(timestamp="2026-05-25T09:00:00-04:00"),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201, response.json()
    sessions = response.json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["status"] == "provisional"


def test_reingest_after_wake_flips_provisional_to_final(monkeypatch):
    """A session first captured mid-stream is provisional; re-posting the
    SAME completed session >30 min after wake must flip it to final
    (and must not create a second row). This is the core settle-on-repoll
    behavior the Shortcut's 30-min polling depends on."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    # First poll: 8 min after the 8:52 AM wake → provisional.
    first = client.post(
        "/api/sleep",
        json=_night_payload(timestamp="2026-05-25T09:00:00-04:00"),
        headers=headers,
    )
    assert first.status_code == 201
    assert first.json()["sessions"][0]["status"] == "provisional"

    # Later poll of the same finished night, >3h after wake → final.
    second = client.post(
        "/api/sleep",
        json=_night_payload(timestamp="2026-05-25T12:00:00-04:00"),
        headers=headers,
    )
    assert second.status_code == 201
    assert second.json()["sessions"][0]["status"] == "final"
    assert _count_sleep(engine, user_id=1) == 1  # still one row


def test_reingest_does_not_create_duplicate_feed_post(monkeypatch):
    """A finalized night posts to the feed exactly once. Re-polling the
    same finished session must NOT create a second 'sleep' post."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    # Two polls of the same finished night (both final).
    client.post("/api/sleep", json=_night_payload(), headers=headers)
    client.post("/api/sleep", json=_night_payload(), headers=headers)

    with engine.connect() as conn:
        n = conn.execute(
            text(
                "SELECT count(*) FROM posts "
                "WHERE user_id = 1 AND type = 'sleep'"
            )
        ).scalar()
    assert n == 1, f"expected exactly one sleep feed post, got {n}"


def test_night_sleep_date_anchored_to_central_time(monkeypatch):
    """sleep_date is the Central-Time calendar date of the evening the
    night began. The oracle night onsets 12:07 AM at -04:00 (Eastern) =
    11:07 PM CT on May 24, so sleep_date must be 2026-05-24 regardless
    of the phone's UTC offset (and must match the CT-bucketed read
    aggregations)."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/sleep",
        json=_night_payload(),
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )
    assert response.status_code == 201, response.json()
    assert response.json()["sessions"][0]["sleep_date"] == "2026-05-24"


def test_classification_uses_central_time_not_payload_offset(monkeypatch):
    """Onset 8:30 PM at -04:00 (Eastern) is 7:30 PM CT, which is OUTSIDE
    the 20:00-05:00 CT night window → 'nap'. Classifying on the payload
    offset would wrongly call it 'night'."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = {
        "values": "Core",
        "starts": "May 25, 2026 at 8:30 PM",
        "ends": "May 25, 2026 at 9:20 PM",
        "types": "Sleep",
        "duration": "50:00",
        "timestamp": "2026-05-25T22:00:00-04:00",
    }
    response = TestClient(main.app).post(
        "/api/sleep",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )
    assert response.status_code == 201, response.json()
    assert response.json()["sessions"][0]["session_type"] == "nap"


# ----- Anti-spoofing ------------------------------------------------------


def test_user_id_in_body_is_ignored(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = _night_payload()
    payload["user_id"] = 999  # ignored — Pydantic drops unknown fields

    response = TestClient(main.app).post(
        "/api/sleep",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    assert response.json()["sessions"][0]["user_id"] == 1  # alice, from token
    assert _count_sleep(engine, user_id=1) == 1
    assert _count_sleep(engine, user_id=999) == 0


# ----- Payload validation -------------------------------------------------


def test_mismatched_array_lengths_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = _night_payload()
    payload["values"] = "Core\nDeep"  # 2 entries while others have 32

    response = TestClient(main.app).post(
        "/api/sleep",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 422
    assert _count_sleep(engine) == 0


def test_missing_offset_in_timestamp_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    payload = _night_payload(timestamp="2026-05-25T09:00:00")  # no offset

    response = TestClient(main.app).post(
        "/api/sleep",
        json=payload,
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 422
    assert _count_sleep(engine) == 0
