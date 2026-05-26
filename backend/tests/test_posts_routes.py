"""HTTP-level tests for /api/posts/*.

Exercises the wire: feed reads, per-user feeds, the write path with
Bearer-token auth, the type CHECK constraint, and the
no-spoofing-via-body guard.
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app import db, main


ALICE_TOKEN = "alice_token_aaaaaaaaaaaaaaaaaaaaaaaa"
BOB_TOKEN = "bob_token_bbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _engine_with_users(seed_posts: bool = False):
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
        if seed_posts:
            conn.execute(
                text(
                    "INSERT INTO posts (user_id, username, type, timestamp) "
                    "VALUES (:uid, :u, :t, :ts)"
                ),
                [
                    {
                        "uid": 1,
                        "u": "alice",
                        "t": "steps",
                        "ts": "2026-05-23T08:00:00",
                    },
                    {
                        "uid": 1,
                        "u": "alice",
                        "t": "sleep",
                        "ts": "2026-05-22T22:00:00",
                    },
                    {
                        "uid": 2,
                        "u": "bob",
                        "t": "workout",
                        "ts": "2026-05-23T18:00:00",
                    },
                ],
            )
    return engine


def _count_posts(engine, user_id=None) -> int:
    with engine.connect() as conn:
        if user_id is None:
            return int(conn.execute(text("SELECT count(*) FROM posts")).scalar() or 0)
        return int(
            conn.execute(
                text("SELECT count(*) FROM posts WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar()
            or 0
        )


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def test_post_creates_post_for_token_owner(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/posts",
        json={"type": "steps", "timestamp": "2026-05-23T08:00:00"},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == 1
    assert body["username"] == "alice"  # denormalized from token, not body
    assert body["type"] == "steps"
    assert isinstance(body["id"], int)

    assert _count_posts(engine, user_id=1) == 1


def test_post_without_auth_returns_401(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/posts",
        json={"type": "steps", "timestamp": "2026-05-23T08:00:00"},
    )

    assert response.status_code == 401
    assert _count_posts(engine) == 0


def test_post_rejects_unknown_type(monkeypatch):
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/posts",
        json={"type": "food", "timestamp": "2026-05-23T08:00:00"},
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    # Pydantic Literal rejects this before it ever reaches the DB.
    assert response.status_code == 422
    assert _count_posts(engine) == 0


def test_post_username_resolved_from_token_not_body(monkeypatch):
    """A malicious client sends username='bob' in the body. The post
    must be written under alice (the token's owner)."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).post(
        "/api/posts",
        json={
            "type": "steps",
            "timestamp": "2026-05-23T08:00:00",
            "username": "bob",  # ignored
            "user_id": 999,  # ignored
        },
        headers={"Authorization": f"Bearer {ALICE_TOKEN}"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == 1
    assert response.json()["username"] == "alice"
    assert _count_posts(engine, user_id=1) == 1
    assert _count_posts(engine, user_id=2) == 0


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def test_list_feed_returns_all_posts_newest_first(monkeypatch):
    engine = _engine_with_users(seed_posts=True)
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/posts")

    assert response.status_code == 200
    posts = response.json()["posts"]
    assert len(posts) == 3
    # Bob's workout at 18:00 is newest, alice's steps at 08:00 is middle,
    # alice's sleep at 22:00 prior night is oldest.
    assert posts[0]["username"] == "bob"
    assert posts[0]["type"] == "workout"
    assert posts[-1]["type"] == "sleep"


def test_list_feed_filters_by_type(monkeypatch):
    engine = _engine_with_users(seed_posts=True)
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/posts?type=steps")

    assert response.status_code == 200
    posts = response.json()["posts"]
    assert len(posts) == 1
    assert posts[0]["type"] == "steps"
    assert posts[0]["username"] == "alice"


def test_list_feed_respects_limit(monkeypatch):
    engine = _engine_with_users(seed_posts=True)
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/posts?limit=2")

    assert response.status_code == 200
    assert len(response.json()["posts"]) == 2


def test_list_user_feed_returns_only_their_posts(monkeypatch):
    engine = _engine_with_users(seed_posts=True)
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/posts/users/alice")

    assert response.status_code == 200
    posts = response.json()["posts"]
    assert len(posts) == 2
    assert all(p["username"] == "alice" for p in posts)


def test_list_user_feed_404s_for_unknown_user(monkeypatch):
    engine = _engine_with_users(seed_posts=True)
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/posts/users/carol")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


def test_list_feed_empty_when_no_posts(monkeypatch):
    engine = _engine_with_users()  # no seeded posts
    monkeypatch.setattr(db, "get_engine", lambda: engine)

    response = TestClient(main.app).get("/api/posts")

    assert response.status_code == 200
    assert response.json() == {"posts": []}


def test_post_rejects_system_only_types(monkeypatch):
    """`steps_milestone` and `leaderboard_recap` are system-generated
    types (the milestone helper + daily-recap cron own them). A regular
    POST /api/posts must reject them at the Pydantic boundary so users
    can't spoof milestones or recaps."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    client = TestClient(main.app)
    headers = {"Authorization": f"Bearer {ALICE_TOKEN}"}

    for forbidden in ("steps_milestone", "leaderboard_recap"):
        response = client.post(
            "/api/posts",
            json={"type": forbidden, "timestamp": "2026-05-23T08:00:00"},
            headers=headers,
        )
        assert response.status_code == 422, forbidden

    # Sanity: user-submittable types still work.
    ok = client.post(
        "/api/posts",
        json={"type": "steps", "timestamp": "2026-05-23T08:00:00"},
        headers=headers,
    )
    assert ok.status_code == 201


# ---------------------------------------------------------------------------
# Per-user feed: recap mention inclusion
# ---------------------------------------------------------------------------


def test_user_feed_includes_recap_where_user_appears_in_top(monkeypatch):
    """A leaderboard_recap that mentions a user in details.top must
    appear in that user's feed, even if it was authored by someone else."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    with engine.begin() as conn:
        # Cron attributes the recap to user_id=1 (alice). The recap
        # mentions alice AND bob (user_id=2) in details.top.
        conn.execute(
            text(
                "INSERT INTO posts "
                "(user_id, username, type, timestamp, details, body) "
                "VALUES (1, 'alice', 'leaderboard_recap', "
                "'2026-05-24T11:00:00', :details, 'Yesterday''s top 3')"
            ),
            {
                "details": '{"top":[{"username":"alice","total":9000},'
                           '{"username":"bob","total":7000}],"date":"2026-05-23"}'
            },
        )

    response = TestClient(main.app).get("/api/posts/users/bob")

    assert response.status_code == 200
    posts = response.json()["posts"]
    assert len(posts) == 1
    assert posts[0]["type"] == "leaderboard_recap"


def test_user_feed_excludes_recap_where_user_not_in_top(monkeypatch):
    """A recap whose details.top does NOT include the target user
    must NOT appear in their feed, even though it exists in the table."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    with engine.begin() as conn:
        # Recap mentions only alice — bob is absent.
        conn.execute(
            text(
                "INSERT INTO posts "
                "(user_id, username, type, timestamp, details, body) "
                "VALUES (1, 'alice', 'leaderboard_recap', "
                "'2026-05-24T11:00:00', :details, 'Yesterday''s top 3')"
            ),
            {
                "details": '{"top":[{"username":"alice","total":9000}],'
                           '"date":"2026-05-23"}'
            },
        )

    response = TestClient(main.app).get("/api/posts/users/bob")

    assert response.status_code == 200
    posts = response.json()["posts"]
    assert posts == []


def test_user_feed_dedupes_recap_authored_by_target(monkeypatch):
    """If cron attributes the recap to user X AND X is in details.top,
    the post should appear exactly once in X's feed — not twice."""
    engine = _engine_with_users()
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO posts "
                "(user_id, username, type, timestamp, details, body) "
                "VALUES (1, 'alice', 'leaderboard_recap', "
                "'2026-05-24T11:00:00', :details, 'Yesterday''s top 3')"
            ),
            {
                "details": '{"top":[{"username":"alice","total":9000}],'
                           '"date":"2026-05-23"}'
            },
        )

    response = TestClient(main.app).get("/api/posts/users/alice")

    posts = response.json()["posts"]
    assert len(posts) == 1
