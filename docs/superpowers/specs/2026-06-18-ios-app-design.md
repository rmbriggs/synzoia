# synzoia iOS app: design spec

**Date:** 2026-06-18
**Status:** Approved design, pre-implementation
**Author:** Micah (with Claude)

## 1. Goal

Turn synzoia into a full native iOS app for a private crew. The app rebuilds
the website's screens natively in SwiftUI and adds the one thing a web app
cannot do: read Apple Health and post sleep and steps automatically, so no one
has to enter data by hand or run an Apple Shortcut.

The app talks to the **existing** synzoia backend (FastAPI on Vercel +
Supabase) over the same REST endpoints the website already uses. We change
**zero backend code**.

## 2. Decisions already made (with rationale)

| Decision | Choice | Why |
|---|---|---|
| App type | Full native SwiftUI app | User wants a real native app, not a web wrapper. |
| Backend | Reuse existing FastAPI/Supabase as-is | The backend already accepts HealthKit-shaped sleep and step payloads. Nothing to add. |
| Data layer (v1) | Plain REST over `URLSession`, pull-to-refresh + periodic refetch | Keeps the client to Apple frameworks only (no SPM). The website's live feed uses Supabase Realtime, but for a small crew, refresh-on-open plus pull-to-refresh is good enough for v1. True Realtime parity is an optional Phase 4 enhancement (§9). |
| Dependencies | Apple frameworks only (SwiftUI, HealthKit, URLSession, Security/Keychain) | No SPM packages means no dynamic-framework embedding problems, the #1 XcodeGen gotcha. Simplest possible build for a first iOS project. |
| Sign-in | Keep the existing token model | Backend identity is already a long-lived per-user Bearer token. App mints one at onboarding and stores it in the Keychain. No backend auth changes. |
| Health scope | Both sleep and steps | User asked for both. Backend supports both. |
| Distribution | TestFlight for the crew | Requires the Apple Developer Program ($99/yr). HealthKit fully supported. |
| Repo layout | New `ios/` directory in the synzoia repo (monorepo) | Keeps the API contract next to the client that consumes it. Existing web/Python CI ignores Swift. |
| Project generation | XcodeGen (`project.yml` committed; generated `.xcodeproj` gitignored) | Keeps project config diffable and merge-friendly. |

## 3. Architecture

```
┌──────────────────────────────────┐         ┌───────────────────────────────┐
│  synzoia iOS app (SwiftUI)        │  HTTPS  │  EXISTING backend (unchanged) │
│                                   │ ──────► │  FastAPI on Vercel + Supabase │
│  HealthKitService ─┐              │  REST   │                               │
│                    ├─► SyncEngine ├──POST──►│  POST /api/sleep  (Bearer)    │
│  (Sleep + Steps)  ─┘              │  JSON   │  POST /api/steps  (Bearer)    │
│                                   │         │                               │
│  Feature views ──► APIClient ─────┼──GET───►│  GET  /api/posts  (public)    │
│  (Feed/Board/Crew/Me)             │ ◄────── │  GET  /api/{sleep,steps}/...  │
│                                   │  JSON   │  POST /api/profiles (public)  │
│  KeychainStore (token)            │         │                               │
└──────────────────────────────────┘         └───────────────────────────────┘
```

The app is one target. It is organized into small, independently testable units.

### 3.1 Modules

- **`APIClient`**: thin wrapper over `URLSession`. Holds the base URL, attaches
  the `Authorization: Bearer <token>` header to writes, decodes JSON into Codable
  structs, maps non-2xx responses to a typed `APIError(status, code, message)`
  that mirrors the backend's `{error: {code, message}}` shape. One method per
  endpoint, mirroring the website's `frontend/src/api/*` wrappers. Reads are
  public and need no token.
- **`KeychainStore`**: save / load / clear the token in the iOS Keychain using
  the Security framework. The token is the whole credential, so it never touches
  `UserDefaults` or plain files.
- **`HealthKitService`**: requests read authorization for Sleep Analysis and
  Step Count, queries the relevant samples, returns plain Swift values. No
  networking here.
- **`SyncEngine`**: turns HealthKit values into the exact request bodies the
  backend expects, posts them via `APIClient`, and reports success / failure and
  last-sync time. Both endpoints are safe to call repeatedly (see §5), so this
  can run on launch, on a manual button, and on background delivery.
- **Feature views + view-models**: one SwiftUI view per screen, each backed by
  an `@Observable` view-model that calls `APIClient` and exposes
  loading / loaded / error / empty state.
- **`AppModel`**: top-level state: is there a token (signed in) or not, which
  drives showing onboarding vs the tab bar.

### 3.2 Base URL configuration

The app ships with a single configurable base URL constant.

- **Production:** the synzoia Vercel domain (absolute URL). We confirm and bake
  the exact domain in Phase 1; it is obtainable from the Vercel dashboard or
  `vercel ls`. The website uses same-origin `/api`; the app needs the absolute
  host.
- **Debug builds:** may point at a local FastAPI dev server
  (`http://localhost:8000`) for testing without hitting production. Localhost
  HTTP needs an ATS exception limited to Debug builds only.

## 4. Screens and navigation

The website's real user-facing pages are Feed, Leaderboard, Profile, Users, and
Join. (DbExplorer and StyleGuide are dev tools and are not ported.)

- **Onboarding / Join**: shown when no token exists. Pick a username, the app
  calls `POST /api/profiles`, receives the token, stores it in the Keychain, and
  shows the token once with a "save this" note (there is no password recovery).
  Then it enters the app.
- **Tab bar** (native bottom tabs):
  - **Feed**: `GET /api/posts`, newest-first, pull-to-refresh. Renders each post
    type (sleep, steps, steps_milestone, leaderboard_recap, workout).
  - **Leaderboard**: sleep and steps rankings via the `/ranking` and `/weekly`
    endpoints. A segmented control toggles sleep vs steps.
  - **Crew**: `GET /api/profiles` list; tapping a person opens their Profile.
  - **Me**: the current user's profile summary plus Settings: Apple Health
    permission status, a "Sync now" button, last-sync time and result, and the
    saved token (so the user is never locked out).
- **Profile** (`/u/:username` equivalent): per-user sleep and steps summaries
  via `/api/{sleep,steps}/users/{username}/summary` and the daily/weekly/monthly
  endpoints.

## 5. Apple Health sync design

### 5.1 Permission

On first launch (after onboarding) the app requests **read-only** authorization
for two HealthKit types: Sleep Analysis (`HKCategoryType .sleepAnalysis`) and
Step Count (`HKQuantityType .stepCount`). Info.plist must include
`NSHealthShareUsageDescription` with a clear, honest reason. We do not write to
HealthKit, so `NSHealthUpdateUsageDescription` is not needed. The app needs the
HealthKit capability/entitlement.

### 5.2 Sleep sync

Mirrors the existing Shortcut, which "polls and sends the full night-plus-naps
window." The app reads the last ~36 hours of Sleep Analysis samples and builds
the `POST /api/sleep` body, where each field is a single newline-joined string,
index-aligned across fields:

```
values    one entry per sample
starts    ISO-8601 UTC start per sample
ends      ISO-8601 UTC end per sample
types     stage name per sample (Core, Deep, REM, Awake, InBed, ...)
duration  minutes per sample (as strings)
timestamp single ISO-8601 with offset = capture moment (drives local wall clock)
```

The server sessionizes, classifies night vs nap, computes metrics, and
**overlap-dedups via upsert**, so re-posting the same window updates the same
rows instead of duplicating. Therefore the app may post freely. The mapping from
`HKCategoryValueSleepAnalysis` cases to the `types` strings is the most
bug-prone piece and gets dedicated unit tests (see §8).

### 5.3 Steps sync

The backend computes a day's steps as **MAX(total) per Central-Time day**, not a
sum (confirmed in `backend/app/services/steps.py`). So the app posts a
**cumulative daily snapshot**: read today's running total step count from
HealthKit and `POST /api/steps` with `{timestamp: now-with-offset, total:
todaysCumulativeSteps}`. Re-posting a higher total later in the day simply raises
the day's MAX. No double-counting. The same write also fires server-side
milestone detection.

### 5.4 When sync runs

- On app foreground / launch.
- On the manual "Sync now" button in Settings.
- **Phase 4:** automatically via HealthKit background delivery
  (`HKObserverQuery` + `enableBackgroundDelivery`), so a night posts without the
  user opening the app.

All sync results (timestamp, what was posted, success/failure) are recorded so
Settings can show a simple sync history and surface errors instead of failing
silently.

## 6. API contract (reference)

Full, verified contract lives in the API map produced during design. Endpoints
the app uses:

**Writes (Bearer token):**
- `POST /api/profiles` → `{username, token, join_date}` (public; mints token)
- `POST /api/sleep` → `{sessions: [...]}` (newline-joined sample window)
- `POST /api/steps` → `{id, user_id, timestamp, total}` (`{timestamp, total}` body)

**Reads (public, no token):**
- `GET /api/posts?limit=&type=` and `GET /api/posts/users/{username}`
- `GET /api/profiles`
- `GET /api/sleep/ranking|weekly|daily|summary`
- `GET /api/sleep/users/{username}/{daily|weekly|monthly|summary}`
- `GET /api/steps/ranking|weekly|daily|summary`
- `GET /api/steps/users/{username}/{daily|weekly|monthly|summary}`
- `GET /api/health` (used to verify base URL during setup)

Errors are `{error: {code, message}}` with standard statuses (401 unauth, 404
not found, 409 username_taken, 422 validation). Response datetimes are ISO-8601
without offset (treat as server-local); request datetimes are ISO-8601 **with**
offset.

## 7. Project setup and tooling

- **Location:** `ios/` in the synzoia repo. `project.yml` (XcodeGen) is the
  source of truth; the generated `synzoia.xcodeproj` and DerivedData are
  gitignored. Add Swift/Xcode entries to the repo `.gitignore`.
- **Bundle identifier:** default `com.synzoia.ios` (configurable; must be unique
  within the user's Apple account). Set in the target settings in `project.yml`.
- **Deployment target:** iOS 17.0 (lets us use `@Observable`; comfortably recent
  for a crew app). Revisit only if a crew member is on something older.
- **Swift:** 6.x (matches installed toolchain).
- **Build surfaces:**
  - Simulator builds and unit tests run from the command line (CI-style),
    HealthKit testable with manually-added sample data in the simulator's Health
    app.
  - Device builds and TestFlight require signing through Xcode (the user selects
    their Team once; Claude cannot click in the GUI or plug in a device).

### 7.1 Division of labor

- **Claude does:** all Swift code, `project.yml`, project generation, simulator
  builds + unit tests from the command line, compile-error fixes, UI iteration
  via simulator screenshots, `brew install xcodegen`.
- **User does (GUI / account only):** accept Xcode license + download iOS
  platform (Phase 0 commands), enroll in the Apple Developer Program ($99) when
  reaching device/TestFlight, select the signing Team in Xcode once, plug in and
  trust the iPhone, click Run for the first device build, and push the TestFlight
  build.

## 8. Testing strategy

Unit tests (XCTest), runnable headless on the simulator with no device or
account:

- **APIClient:** request building (path, headers, Bearer attachment) and JSON
  decoding against recorded sample response bodies for each endpoint. Network is
  mocked (`URLProtocol` stub), so tests never hit the live backend.
- **HealthKit mapping:** a fixed set of sleep samples maps to the exact
  `/api/sleep` newline-joined body; a known cumulative step count maps to the
  exact `/api/steps` body. This is the highest-value test surface.
- **KeychainStore:** save / load / clear round-trips.
- **View-models:** loading / loaded / error / empty transitions, following the
  iOS skill's `@MainActor` testing guidance.

Device-only behaviors (real HealthKit reads, background delivery, TestFlight
install) get a short manual checklist run on the user's phone at each relevant
phase boundary.

## 9. Phased delivery

Each phase ends green on the simulator; from Phase 2 on, each also runs on the
user's phone.

- **Phase 0: Environment + skeleton.** Accept license, download iOS platform,
  install xcodegen, create `ios/project.yml`, generate the project, ship an empty
  app that launches on the simulator. Proves the toolchain end to end.
- **Phase 1: Identity + Feed.** `KeychainStore`, `APIClient`, onboarding
  (`POST /api/profiles` → token → Keychain), read-only Feed from the live
  backend. First "this is real" moment. (Still simulator-only; no $99 yet.)
- **Phase 2: Sleep sync.** HealthKit permission, read sleep, `SyncEngine`,
  `POST /api/sleep`, manual "Sync now". First real-device run (a free Apple ID
  works for 7-day device testing of the HealthKit flow before paying).
- **Phase 3: Steps + remaining screens.** Steps snapshot sync, Leaderboard,
  Crew/Users, Profile, Settings. App reaches feature parity with the website.
- **Phase 4: Background sync + polish.** HealthKit background delivery, app
  icon, loading/error/empty states, transitions. Optional: live-feed parity by
  subscribing to Supabase Realtime on `posts` (this adds the one third-party
  package, `supabase-swift`, and the manual "Embed & Sign" step from the iOS
  skill). If skipped, the feed stays pull-to-refresh + periodic refetch.
- **Phase 5: TestFlight.** Enroll in the Developer Program, archive, upload,
  invite the crew.

## 10. Out of scope (for now)

- Backend changes of any kind (auth upgrade, new endpoints).
- "Sign in with Apple" / real account recovery (possible future upgrade).
- Group chat / reactions (not present in the shipped website).
- Live Supabase Realtime feed in v1. The website *does* use Realtime for the
  feed, but matching it requires the `supabase-swift` package, so it is deferred
  to the optional Phase 4 enhancement. v1 uses pull-to-refresh + periodic refetch.
- Android, iPad-specific layouts, widgets, watchOS app.

## 11. Open items to confirm during implementation

1. **Exact production base URL**: confirm the synzoia Vercel domain in Phase 1
   (Vercel dashboard or `vercel ls`); bake it into the production config.
2. **Bundle identifier**: confirm `com.synzoia.ios` or the user's preference
   before the first signed build.
3. **Sleep `types` string vocabulary**: confirm the exact stage strings the
   server's sessionizer accepts (read `services/sleep_sessions.py`) so the
   HealthKit mapping matches byte-for-byte. The existing Shortcut payload and
   tests are the reference.
