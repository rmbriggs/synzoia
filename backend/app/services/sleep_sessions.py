"""Sleep sessionization service.

Replaces the old single-row-per-night write path. The iOS Shortcut
now sends *raw* HealthKit samples (one row per sleep stage segment)
several times a day, and the backend does all the math:

    1. Parse the newline-joined payload into samples.
    2. Walk samples in time order and split on >60-min gaps into
       sessions (so a night and a daytime nap become two sessions).
    3. Drop sessions under 10 min asleep (noise).
    4. Classify each session as 'night' (onset 20:00-05:00 CT) or
       'nap' (else).
    5. Compute per-session metrics: time in bed, total asleep, awake
       time, per-stage minutes, wakeup count, efficiency.
    6. Overlap-dedup against existing rows (same user, [onset, wake]
       windows that overlap within 30 min) — updates the existing
       row to the later wake/captured_at rather than inserting a
       duplicate. This makes the Shortcut's 30-minute polling cadence
       idempotent.
    7. Mark each row provisional (captured_at − wake < 30 min) or
       final (>= 30 min). Final rows are authoritative; provisional
       rows are mid-session snapshots that will be replaced.

The route layer is intentionally thin — see routes/sleep.py. All the
domain logic lives here so it's testable as plain functions.

Per CLAUDE.md:
    - Identifiers (table/column names) never come from request input.
    - SQL is parameterized via `text()` + bind params.
    - user_id is resolved from the Bearer token, NEVER the body.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Connection


# ----- Constants ----------------------------------------------------------

# Central Time anchors all date-of-day logic (per project convention).
APP_TZ = ZoneInfo("America/Chicago")

# Walk samples in start-order; if start[i] − end[i-1] > this, split into
# a new session. 60 min cleanly separates a normal night from any
# daytime nap, and absorbs short bathroom-break Awake gaps within a
# single night.
SESSION_GAP_MIN = 60

# A session with less than this many minutes of actual asleep time is
# noise (e.g., a brief sit-down the watch mistakenly logged).
MIN_SESSION_ASLEEP_MIN = 10

# Per-session asleep totals above this are physically implausible (>16h
# in a single sleep). Treat as data error rather than store them.
MAX_SESSION_ASLEEP_MIN = 16 * 60

# Stage-name strings the iOS payload uses. Anything not in {Core, Deep,
# REM} is treated as awake-during-bed for asleep/awake accounting; only
# the exact string "Awake" counts as awake for wakeup-count purposes.
STAGE_CORE = "Core"
STAGE_DEEP = "Deep"
STAGE_REM = "REM"
STAGE_AWAKE = "Awake"
ASLEEP_STAGES = frozenset({STAGE_CORE, STAGE_DEEP, STAGE_REM})

# A run of Awake under this length doesn't count as a wakeup (could be
# a single arousal, a roll-over, an HRV blip).
WAKEUP_MIN_MIN = 5

# A session's status is 'provisional' while it might still be in
# progress; it becomes 'final' once we're confident it won't grow.
PROVISIONAL_WINDOW_MIN = 30

# Two sessions overlap (for dedup) if their [onset, wake] intervals
# touch within this slop. Absorbs onset jitter between consecutive
# polls of the same in-progress night.
OVERLAP_SLOP_MIN = 30

# Onset hours that mark a session as a "night" rather than a "nap".
# 20:00-05:00 CT covers the typical sleep window plus late-night and
# graveyard-shift starts. A long afternoon doze still classifies as
# a nap; a short 2 AM sleep still classifies as a night.
NIGHT_ONSET_START_H = 20  # inclusive
NIGHT_ONSET_END_H = 5     # exclusive

# Sessions in the ambiguous band get review_flag=true (but keep their
# classification — the consumer decides what to do with the flag).
LONG_NAP_MIN = 4 * 60
SHORT_NIGHT_MIN = 2 * 60


# ----- Dataclasses --------------------------------------------------------


@dataclass(frozen=True)
class RawSample:
    """One sleep-stage segment as the iOS Shortcut sends it."""
    start: datetime
    end: datetime
    value: str
    dur_sec: int


@dataclass
class SessionRecord:
    """A finalized (or provisional) session, ready to upsert/return."""
    onset: datetime
    wake: datetime
    sleep_date: date
    session_type: str           # 'night' | 'nap'
    status: str                 # 'provisional' | 'final'
    review_flag: bool
    total_asleep_min: int
    time_in_bed_min: int
    awake_min: int
    core_min: int
    deep_min: int
    rem_min: int
    wakeups: int
    efficiency: float           # 0.0 - 1.0
    captured_at: datetime

    # Populated after upsert (id from DB row).
    id: Optional[int] = None
    user_id: Optional[int] = None


class SleepPayloadError(ValueError):
    """Raised when the iOS payload is structurally invalid (mismatched
    lengths, unparseable timestamps, etc.). Route layer maps to 422."""


# ----- Parsing ------------------------------------------------------------


_SAMPLE_DATE_RE = re.compile(
    # "May 25, 2026 at 12:07 AM"
    # %b — abbreviated month
    # %-d on POSIX, but Python strptime accepts %d with leading zero;
    # the inbound stream uses no leading zero, so we accept either via
    # explicit format with `%d` plus a strip — or we substitute zero-
    # padding before parsing. Simplest: replace the parsed result
    # through strptime with both formats.
    r"^(?P<rest>.+)$"
)


def _parse_sample_dt(s: str, offset: timezone) -> datetime:
    """Parse 'May 25, 2026 at 12:07 AM' + apply the payload's offset
    (the wall clock in the user's local zone)."""
    # `%d` requires leading zero on non-GNU; pad day if absent.
    # "May 5, 2026 at 1:07 AM" → "May 05, 2026 at 01:07 AM"
    s = s.strip()
    # Insert leading zero on day.
    s = re.sub(r"^(\w+) (\d), ", lambda m: f"{m.group(1)} 0{m.group(2)}, ", s)
    # Insert leading zero on hour.
    s = re.sub(r" at (\d):", lambda m: f" at 0{m.group(1)}:", s)
    try:
        naive = datetime.strptime(s, "%b %d, %Y at %I:%M %p")
    except ValueError as e:
        raise SleepPayloadError(f"Unparseable timestamp {s!r}") from e
    return naive.replace(tzinfo=offset)


def _parse_duration_sec(s: str) -> int:
    """'14:01' → 841, '30' → 30. Anything else raises."""
    s = s.strip()
    if not s:
        raise SleepPayloadError("Empty duration value")
    if ":" in s:
        parts = s.split(":")
        if len(parts) != 2:
            raise SleepPayloadError(f"Bad duration format {s!r}")
        try:
            mins, secs = int(parts[0]), int(parts[1])
        except ValueError as e:
            raise SleepPayloadError(f"Non-numeric duration {s!r}") from e
        if mins < 0 or secs < 0 or secs >= 60:
            raise SleepPayloadError(f"Out-of-range duration {s!r}")
        return mins * 60 + secs
    try:
        secs = int(s)
    except ValueError as e:
        raise SleepPayloadError(f"Non-numeric duration {s!r}") from e
    if secs < 0:
        raise SleepPayloadError(f"Negative duration {s!r}")
    return secs


def _offset_from_timestamp(ts: str) -> timezone:
    """'2026-06-01T09:02:37-04:00' → tzinfo(-04:00)."""
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError as e:
        raise SleepPayloadError(f"Bad capture timestamp {ts!r}") from e
    if dt.tzinfo is None:
        # No offset means we don't know the user's wall clock; reject
        # rather than guess.
        raise SleepPayloadError(
            f"Capture timestamp {ts!r} has no UTC offset; "
            "Shortcut should send ISO-8601 with offset"
        )
    return dt.tzinfo  # type: ignore[return-value]


def parse_payload(
    values: str,
    starts: str,
    ends: str,
    types: str,
    duration: str,
    timestamp: str,
) -> tuple[list[RawSample], datetime, timezone]:
    """Parse the six raw payload fields into samples + capture time.

    Returns (samples_sorted_by_start, capture_dt, payload_offset).
    Raises SleepPayloadError on any structural problem.
    """
    capture_dt = datetime.fromisoformat(timestamp)
    offset = _offset_from_timestamp(timestamp)

    value_arr = values.split("\n")
    start_arr = starts.split("\n")
    end_arr = ends.split("\n")
    type_arr = types.split("\n")
    dur_arr = duration.split("\n")

    n = len(value_arr)
    if not all(len(arr) == n for arr in (start_arr, end_arr, type_arr, dur_arr)):
        raise SleepPayloadError(
            f"Mismatched array lengths: values={len(value_arr)}, "
            f"starts={len(start_arr)}, ends={len(end_arr)}, "
            f"types={len(type_arr)}, duration={len(dur_arr)}"
        )
    if n == 0:
        raise SleepPayloadError("Empty payload")

    samples: list[RawSample] = []
    for v, s, e, _t, d in zip(value_arr, start_arr, end_arr, type_arr, dur_arr):
        samples.append(
            RawSample(
                start=_parse_sample_dt(s, offset),
                end=_parse_sample_dt(e, offset),
                value=v.strip(),
                dur_sec=_parse_duration_sec(d),
            )
        )
    samples.sort(key=lambda s: s.start)
    return samples, capture_dt, offset


# ----- Sessionization -----------------------------------------------------


def split_into_sessions(samples: list[RawSample]) -> list[list[RawSample]]:
    """Walk samples in start-order. Begin a new session whenever
    start[i] - end[i-1] > SESSION_GAP_MIN."""
    if not samples:
        return []
    sessions: list[list[RawSample]] = [[samples[0]]]
    gap = timedelta(minutes=SESSION_GAP_MIN)
    for s in samples[1:]:
        prev_end = sessions[-1][-1].end
        if s.start - prev_end > gap:
            sessions.append([s])
        else:
            sessions[-1].append(s)
    return sessions


def _count_wakeups(samples: list[RawSample]) -> int:
    """Distinct runs of Awake samples whose total length ≥ WAKEUP_MIN_MIN."""
    runs: list[int] = []  # seconds per Awake run
    current = 0
    for s in samples:
        if s.value == STAGE_AWAKE:
            current += s.dur_sec
        else:
            if current > 0:
                runs.append(current)
                current = 0
    if current > 0:
        runs.append(current)
    threshold = WAKEUP_MIN_MIN * 60
    return sum(1 for r in runs if r >= threshold)


def _onset_of(samples: list[RawSample]) -> datetime:
    """First non-Awake sample's start; falls back to first sample's
    start if every sample is Awake (vanishingly rare)."""
    for s in samples:
        if s.value != STAGE_AWAKE:
            return s.start
    return samples[0].start


def _classify_session_type(onset_ct: datetime) -> str:
    """20:00-05:00 Central Time → night; else nap. `onset_ct` must
    already be expressed in Central Time (see _to_ct) — per the project
    convention all date-of-day logic is CT-anchored, not phone-local."""
    h = onset_ct.hour
    if h >= NIGHT_ONSET_START_H or h < NIGHT_ONSET_END_H:
        return "night"
    return "nap"


def _to_ct(dt: datetime) -> datetime:
    """`dt` expressed in Central Time. Naive datetimes are assumed UTC,
    which is how they're stored in / read back from the DB."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(APP_TZ)


def build_session_record(
    samples: list[RawSample],
    capture_dt: datetime,
) -> Optional[SessionRecord]:
    """Compute metrics + classify one session's samples. Returns None
    when the session is below the noise floor or above the sanity cap
    (caller drops these silently)."""
    if not samples:
        return None

    total_asleep_sec = sum(
        s.dur_sec for s in samples if s.value in ASLEEP_STAGES
    )
    if total_asleep_sec < MIN_SESSION_ASLEEP_MIN * 60:
        return None  # noise
    if total_asleep_sec > MAX_SESSION_ASLEEP_MIN * 60:
        return None  # sanity guard — gap threshold failed to split

    onset = _onset_of(samples)
    wake = samples[-1].end
    time_in_bed_sec = max(0, int((wake - onset).total_seconds()))

    core_sec = sum(s.dur_sec for s in samples if s.value == STAGE_CORE)
    deep_sec = sum(s.dur_sec for s in samples if s.value == STAGE_DEEP)
    rem_sec = sum(s.dur_sec for s in samples if s.value == STAGE_REM)
    awake_sec = sum(s.dur_sec for s in samples if s.value == STAGE_AWAKE)

    onset_ct = _to_ct(onset)
    session_type = _classify_session_type(onset_ct)
    total_asleep_min = total_asleep_sec // 60
    review_flag = (
        (session_type == "nap" and total_asleep_min > LONG_NAP_MIN)
        or (session_type == "night" and total_asleep_min < SHORT_NIGHT_MIN)
    )

    age = capture_dt - wake
    status = (
        "provisional"
        if age < timedelta(minutes=PROVISIONAL_WINDOW_MIN)
        else "final"
    )

    efficiency = (
        total_asleep_sec / time_in_bed_sec if time_in_bed_sec > 0 else 0.0
    )

    # For sleep_date grouping: a night belongs to the CT date of the
    # evening it began. An onset in the early-morning hours (before
    # 05:00 CT) is the tail of the previous evening's night, so it rolls
    # back one day; an evening onset (>= 20:00 CT) and naps use the
    # onset's own CT date. Everything is CT-anchored (via onset_ct) so
    # sleep_date matches the CT-bucketed read-side aggregations.
    onset_ct_date = onset_ct.date()
    sleep_date = (
        onset_ct_date - timedelta(days=1)
        if session_type == "night" and onset_ct.hour < NIGHT_ONSET_END_H
        else onset_ct_date
    )

    return SessionRecord(
        onset=onset,
        wake=wake,
        sleep_date=sleep_date,
        session_type=session_type,
        status=status,
        review_flag=review_flag,
        total_asleep_min=total_asleep_min,
        time_in_bed_min=time_in_bed_sec // 60,
        awake_min=awake_sec // 60,
        core_min=core_sec // 60,
        deep_min=deep_sec // 60,
        rem_min=rem_sec // 60,
        wakeups=_count_wakeups(samples),
        efficiency=round(efficiency, 4),
        captured_at=capture_dt,
    )


def build_sessions(
    samples: list[RawSample], capture_dt: datetime
) -> list[SessionRecord]:
    """Full pipeline: split → metric per session → drop noise/sanity-
    failed sessions. Returns sessions in start-time order."""
    out: list[SessionRecord] = []
    for group in split_into_sessions(samples):
        rec = build_session_record(group, capture_dt)
        if rec is not None:
            out.append(rec)
    return out


# ----- Persistence (overlap dedup) ----------------------------------------


def _aware_to_naive_utc(dt: datetime) -> datetime:
    """Sleep table columns are naive timestamps (per project convention,
    matching steps.timestamp). Convert offset-aware to UTC naive on the
    way in so storage stays uniform."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _coerce_db_dt(raw) -> datetime:
    """SQLite returns TIMESTAMP columns as ISO strings; Postgres returns
    naive `datetime`. Normalize to naive datetime for comparison."""
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None) if raw.tzinfo else raw
    return datetime.fromisoformat(str(raw))


def _find_overlapping_session(
    conn: Connection, user_id: int, onset: datetime, wake: datetime
) -> Optional[dict]:
    """Find an existing sleep row whose [onset_at, wake_time] overlaps
    [onset, wake] within OVERLAP_SLOP_MIN minutes. Returns the row dict
    or None. If multiple match (shouldn't happen with sane data) we
    take the most recently captured."""
    slop = timedelta(minutes=OVERLAP_SLOP_MIN)
    o_naive = _aware_to_naive_utc(onset)
    w_naive = _aware_to_naive_utc(wake)

    row = (
        conn.execute(
            text(
                "SELECT id, onset_at, wake_time, captured_at "
                "FROM sleep "
                "WHERE user_id = :uid "
                "  AND onset_at < :wake_plus "
                "  AND wake_time > :onset_minus "
                "ORDER BY captured_at DESC "
                "LIMIT 1"
            ),
            {
                "uid": user_id,
                "wake_plus": w_naive + slop,
                "onset_minus": o_naive - slop,
            },
        )
        .mappings()
        .first()
    )
    return dict(row) if row is not None else None


def _insert_session(
    conn: Connection, user_id: int, rec: SessionRecord
) -> tuple[int, datetime, datetime, datetime]:
    onset_naive = _aware_to_naive_utc(rec.onset)
    wake_naive = _aware_to_naive_utc(rec.wake)
    captured_naive = _aware_to_naive_utc(rec.captured_at)
    row = (
        conn.execute(
            text(
                "INSERT INTO sleep ("
                "  user_id, bedtime, wake_time, duration_min, "
                "  rem_minutes, core_minutes, deep_minutes, awake_minutes, "
                "  night_of, session_type, status, review_flag, "
                "  captured_at, onset_at, sleep_date"
                ") VALUES ("
                "  :uid, :bedtime, :wake, :dur_min, "
                "  :rem, :core, :deep, :awake, "
                "  :night_of, :session_type, :status, :review_flag, "
                "  :captured, :onset, :sleep_date"
                ") RETURNING id, onset_at, wake_time, captured_at"
            ),
            {
                "uid": user_id,
                "bedtime": onset_naive,
                "wake": wake_naive,
                "dur_min": rec.total_asleep_min,
                "rem": rec.rem_min,
                "core": rec.core_min,
                "deep": rec.deep_min,
                "awake": rec.awake_min,
                "night_of": rec.sleep_date,
                "session_type": rec.session_type,
                "status": rec.status,
                "review_flag": rec.review_flag,
                "captured": captured_naive,
                "onset": onset_naive,
                "sleep_date": rec.sleep_date,
            },
        )
        .mappings()
        .one()
    )
    return (
        int(row["id"]),
        row["onset_at"],
        row["wake_time"],
        row["captured_at"],
    )


def _update_session(
    conn: Connection, row_id: int, rec: SessionRecord
) -> None:
    onset_naive = _aware_to_naive_utc(rec.onset)
    wake_naive = _aware_to_naive_utc(rec.wake)
    captured_naive = _aware_to_naive_utc(rec.captured_at)
    conn.execute(
        text(
            "UPDATE sleep SET "
            "  bedtime = :bedtime, "
            "  wake_time = :wake, "
            "  duration_min = :dur_min, "
            "  rem_minutes = :rem, "
            "  core_minutes = :core, "
            "  deep_minutes = :deep, "
            "  awake_minutes = :awake, "
            "  night_of = :night_of, "
            "  session_type = :session_type, "
            "  status = :status, "
            "  review_flag = :review_flag, "
            "  captured_at = :captured, "
            "  onset_at = :onset, "
            "  sleep_date = :sleep_date "
            "WHERE id = :id"
        ),
        {
            "id": row_id,
            "bedtime": onset_naive,
            "wake": wake_naive,
            "dur_min": rec.total_asleep_min,
            "rem": rec.rem_min,
            "core": rec.core_min,
            "deep": rec.deep_min,
            "awake": rec.awake_min,
            "night_of": rec.sleep_date,
            "session_type": rec.session_type,
            "status": rec.status,
            "review_flag": rec.review_flag,
            "captured": captured_naive,
            "onset": onset_naive,
            "sleep_date": rec.sleep_date,
        },
    )


def upsert_session(
    conn: Connection, user_id: int, rec: SessionRecord
) -> SessionRecord:
    """Insert the session OR merge into an overlapping existing row.

    Merge rule: keep the version with the later wake (more complete);
    take the incoming session's metrics + classification + status +
    captured_at since it's the fresher snapshot. The DB id is
    preserved across merges so foreign keys (when any) keep referring
    to the same logical session."""
    existing = _find_overlapping_session(conn, user_id, rec.onset, rec.wake)

    if existing is None:
        row_id, onset_db, wake_db, captured_db = _insert_session(
            conn, user_id, rec
        )
        out = rec
        out.id = row_id
        out.user_id = user_id
        # Normalize tz state to match the existing-row branch below, which
        # reads back through `_coerce_db_dt` and therefore returns NAIVE
        # datetimes. Without this, a payload that contains a mix of
        # brand-new sessions (this branch — aware) and overlapping
        # sessions (other branch — naive) blows up downstream when the
        # route does `max(sessions, key=lambda s: s.wake)` with
        # "can't compare offset-naive and offset-aware datetimes."
        out.onset = _coerce_db_dt(onset_db)
        out.wake = _coerce_db_dt(wake_db)
        out.captured_at = _coerce_db_dt(captured_db)
        return out

    # Adopt the incoming snapshot when it is at least as complete (wake)
    # AND at least as fresh (captured_at). The equal-wake case is the
    # common one: the Shortcut re-polls a *finished* session (identical
    # wake) hours later — that snapshot has a newer captured_at and a
    # recomputed status, so it must replace the row to flip
    # provisional → final. Only a strictly-later wake or an equal wake
    # with a newer capture wins; a stale/less-complete poll must never
    # downgrade an already-final row.
    # SQLite returns timestamps as strings, Postgres returns datetime;
    # normalize both sides to naive UTC datetime for comparison.
    existing_wake = _coerce_db_dt(existing["wake_time"])
    existing_captured = _coerce_db_dt(existing["captured_at"])
    incoming_wake = _aware_to_naive_utc(rec.wake)
    incoming_captured = _aware_to_naive_utc(rec.captured_at)
    if incoming_wake > existing_wake or (
        incoming_wake == existing_wake
        and incoming_captured >= existing_captured
    ):
        _update_session(conn, int(existing["id"]), rec)
    else:
        # Older or less-complete snapshot — only bump captured_at, and
        # never below the current value or in a way that touches status.
        conn.execute(
            text(
                "UPDATE sleep SET captured_at = :captured "
                "WHERE id = :id AND captured_at < :captured"
            ),
            {
                "id": int(existing["id"]),
                "captured": incoming_captured,
            },
        )

    # Read back the (now-merged) row so the caller gets canonical state.
    row = (
        conn.execute(
            text(
                "SELECT id, user_id, bedtime, wake_time, duration_min, "
                "rem_minutes, core_minutes, deep_minutes, awake_minutes, "
                "night_of, session_type, status, review_flag, "
                "captured_at, onset_at, sleep_date "
                "FROM sleep WHERE id = :id"
            ),
            {"id": int(existing["id"])},
        )
        .mappings()
        .one()
    )

    onset_db = _coerce_db_dt(row["onset_at"])
    wake_db = _coerce_db_dt(row["wake_time"])
    time_in_bed_sec = int((wake_db - onset_db).total_seconds())
    return SessionRecord(
        onset=onset_db,
        wake=wake_db,
        sleep_date=row["sleep_date"]
        if isinstance(row["sleep_date"], date)
        else date.fromisoformat(str(row["sleep_date"])),
        session_type=row["session_type"],
        status=row["status"],
        review_flag=bool(row["review_flag"]),
        total_asleep_min=int(row["duration_min"]),
        time_in_bed_min=max(0, time_in_bed_sec // 60),
        awake_min=int(row["awake_minutes"] or 0),
        core_min=int(row["core_minutes"] or 0),
        deep_min=int(row["deep_minutes"] or 0),
        rem_min=int(row["rem_minutes"] or 0),
        wakeups=rec.wakeups,  # not stored; carry over from incoming
        efficiency=rec.efficiency,  # not stored; carry over from incoming
        captured_at=_coerce_db_dt(row["captured_at"]),
        id=int(row["id"]),
        user_id=int(row["user_id"]),
    )


# ----- Top-level entry point ----------------------------------------------


def ingest_payload(
    conn: Connection,
    user_id: int,
    values: str,
    starts: str,
    ends: str,
    types: str,
    duration: str,
    timestamp: str,
) -> list[SessionRecord]:
    """Parse → sessionize → upsert each session. Returns the persisted
    sessions (including any merges) in onset-time order."""
    samples, capture_dt, _offset = parse_payload(
        values=values,
        starts=starts,
        ends=ends,
        types=types,
        duration=duration,
        timestamp=timestamp,
    )
    sessions = build_sessions(samples, capture_dt)
    persisted: list[SessionRecord] = []
    for s in sessions:
        persisted.append(upsert_session(conn, user_id, s))
    return persisted
