"""HTTP-level tests for POST /api/steps + Bearer-token auth.

The write path resolves `user_id` from the `Authorization: Bearer
<token>` header. These tests exercise the wire: valid token inserts
a row, missing/bad token returns 401 with no row written, and the
inserted row is owned by the right user (never spoofable via body).
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


ALICE_TOKEN = "alice_token_aaaaaaaaaaaaaaaaaaaaaaaa"
BOB_TOKEN = "bob_token_bbbbbbbbbbbbbbbbbbbbbbbbbbbb"


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
                "VALUES (:u, :t, :j)"
            ),
            [
                {"u": "alice", "t": ALICE_TOKEN, "j": "2026-05-01T00:00:00"},
                {"u": "bob", "t": BOB_TOKEN, "j": "2026-05-01T00:00:00"},
            ],
        )
    return engine


def _count_steps(engine, user_id: int) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                text("SELECT count(*) FROM steps WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar()
            or 0
        )


def test_post_steps_inserts_row_for_token_owner(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T08:00:00", "total": 8432},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == 1  # alice
    assert body["total"] == 8432
    assert body["timestamp"].startswith("2026-05-23T08:00:00")
    assert isinstance(body["id"], int)

    # Row landed in DB under alice.
    assert _count_steps(engine, user_id=1) == 1
    assert _count_steps(engine, user_id=2) == 0


def test_post_steps_without_auth_header_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T08:00:00", "total": 8432},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    assert _count_steps(engine, user_id=1) == 0


def test_post_steps_with_bad_token_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T08:00:00", "total": 8432},
        headers={"Authorization": "Bearer not_a_real_token"},
    )

    assert response.status_code == 401
    assert _count_steps(engine, user_id=1) == 0


def test_post_steps_with_malformed_auth_header_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    # "Token x" instead of "Bearer x" — also no scheme at all.
    for header in ["Token abc", ALICE_TOKEN, "Bearer "]:
        response = TestClient(main.app).post(
            "/api/steps",
            json={"timestamp": "2026-05-23T08:00:00", "total": 8432},
            headers={"Authorization": header},
        )
        assert response.status_code == 401, header

    assert _count_steps(engine, user_id=1) == 0


def test_post_steps_user_id_is_resolved_from_token_not_body(monkeypatch):
    """Even if a malicious client sends a `user_id` in the JSON body,
    the row must be written under the token-resolved user. This guards
    the CLAUDE.md rule: user_id from JWT, never from request body."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={
            "timestamp": "2026-05-23T08:00:00",
            "total": 8432,
            "user_id": 2,  # bob — should be ignored
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == 1  # alice, from the token
    assert _count_steps(engine, user_id=1) == 1
    assert _count_steps(engine, user_id=2) == 0


def test_post_steps_with_negative_total_returns_422(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/steps",
        json={"timestamp": "2026-05-23T08:00:00", "total": -50},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 422
    assert _count_steps(engine, user_id=1) == 0


def _engine_with_users_and_posts():
    """Returns an engine with profiles, steps, and posts tables
    (post-migration-0007 shape) so milestone-detection tests can
    observe what got inserted. The posts table is now included in
    _engine_with_users() since detect_and_insert_milestone requires it."""
    return _engine_with_users()


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


def test_step_write_5k_then_12k_fires_10k_but_does_not_refire_5k(monkeypatch):
    """The implicit-watermark invariant: once 5k is posted, all
    thresholds <= 5k are already crossed for that day. A subsequent
    jump to 12k should fire 10k only — never re-fire 5k or fire 1k
    after the fact."""
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
        json={"timestamp": "2026-05-23T20:00:00", "total": 12000},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    rows = _milestone_rows(engine, user_id=1)
    assert [r["body"] for r in rows] == [
        "hit 5,000 steps",
        "hit 10,000 steps",
    ]


def test_step_write_does_not_fire_milestone_from_other_ct_day(monkeypatch):
    """Regression: a high step total on one CT day must not trigger a
    milestone on a different CT day. _utc_window deliberately spans
    multiple UTC days to cover CT/UTC boundary, so the detector must
    re-filter rows by actual CT date in Python before taking the max."""
    engine = _engine_with_users_and_posts()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    # UTC 02:30 on 5/24 → CT 21:30 on 5/23. Alice crosses 5k on CT 5/23.
    first = client.post(
        "/api/steps",
        json={"timestamp": "2026-05-24T02:30:00", "total": 9567},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )
    # UTC 00:02 on 5/26 → CT 19:02 on 5/25. Only 955 steps on CT 5/25 —
    # nowhere near a milestone. But the wide UTC window pulls in the
    # 9567 row from CT 5/23 if the detector doesn't re-filter.
    second = client.post(
        "/api/steps",
        json={"timestamp": "2026-05-26T00:02:00", "total": 955},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert first.status_code == 201
    assert second.status_code == 201

    import json as _json
    rows = _milestone_rows(engine, user_id=1)
    details = [_json.loads(r["details"]) for r in rows]
    # Exactly one milestone, for the one CT day she actually crossed 5k.
    assert len(rows) == 1, f"unexpected milestone rows: {details}"
    assert details[0] == {"threshold": 5000, "date": "2026-05-23"}


def test_step_write_milestones_isolated_per_user(monkeypatch):
    """Alice and Bob both posting must produce milestones attributed
    to their own user_id, never each other's."""
    engine = _engine_with_users_and_posts()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)

    a = client.post(
        "/api/steps",
        json={"timestamp": "2026-05-23T18:00:00", "total": 2000},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )
    b = client.post(
        "/api/steps",
        json={"timestamp": "2026-05-23T19:00:00", "total": 7000},
        headers={"Authorization": f"Bearer {BOB_TOKEN}"},
    )

    assert a.status_code == 201
    assert b.status_code == 201
    alice_rows = _milestone_rows(engine, user_id=1)
    bob_rows = _milestone_rows(engine, user_id=2)
    assert len(alice_rows) == 1 and alice_rows[0]["body"] == "hit 1,000 steps"
    assert len(bob_rows) == 1 and bob_rows[0]["body"] == "hit 5,000 steps"
