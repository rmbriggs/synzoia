# synzoia iOS app: Phase 3B Plan (4-tab shell + Ranks / Profile / Groups + endpoints)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes.

**Goal:** Turn the restyled screens (3A) into the full 4-tab app from the design: a coastal tab bar (Feed / Groups / Ranks / You), the new Ranks (steps + sleep leaderboard + podium detail) and You/Profile screens, a Groups "coming soon" placeholder, and the GET endpoints those screens need.

**Architecture:** New read endpoints on `APIClient` (ranking, user summaries, weekly, profiles) with Codable models. New `@MainActor @Observable` view-models per screen, each with loading/loaded/empty/failed states (mirroring `FeedViewModel`). A `MainTabView` styled like the design's tab bar replaces the current `SignedInView` Feed-only root; Settings moves under the You tab. The current user's username is persisted at onboarding so the You tab and "You · #N" highlights work.

**Tech Stack:** SwiftUI, the 3A design system (`SynColor`/`SynFont`/components), URLSession, Observation, XCTest. Apple frameworks only, no SPM.

**Design source:** `sdd/synzoia-app-design.html` (screen line ranges noted per task). Implementers MUST open it for exact styling.

## Global Constraints

- iOS 17.0, Swift 5.0, iPhone only, Apple frameworks only, NO SPM. Work in `~/Developer/synzoia/.claude/worktrees/ios-app` on `feat/ios-app`; after file/`project.yml` changes run `cd ios && xcodegen generate && cd ..`.
- Reuse the 3A design system: `SynColor`, `SynFont`, `SynWordmark`, `GradientAvatar`, `SynCard`, `MonoLabel`, `Pill`, `SleepStageBar`, `WeekBars`. Dark only.
- All new endpoints are public GETs (no token). Decode with the existing `APIClient.decoder` (`.convertFromSnakeCase`).
- **Verified endpoint contracts** (field names shown pre-conversion; e.g. `week_start`->`weekStart`):
  - `GET /api/steps/ranking` and `GET /api/sleep/ranking` -> `{ week_start, week_end, total_steps|total_minutes, leaderboard: [{rank, username, total}], daily_breakdown: [{date, total}] }`. Use `total` from `leaderboard` entries (units differ: steps vs minutes).
  - `GET /api/steps/users/{username}/summary` -> `{ username, join_date, score, best_day: {date, total}|null, rank }` (fields nullable). `GET /api/sleep/users/{username}/summary` -> same but `best_night` instead of `best_day`.
  - `GET /api/steps/users/{username}/weekly` -> `{ username, week_start, week_end, weekly_total, rank_this_week, daily_breakdown: [{date, total}] }` (7 entries for the bar chart).
  - `GET /api/profiles` -> `{ profiles: [{username, join_date, total_steps_all_time}] }`.
- No em dashes anywhere. Commit bodies end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Test simulator `iPhone 17`. Verify each task: build green + 35-plus tests green; screen tasks also screenshot vs the design (use the sim test hook `SIMCTL_CHILD_SYNZOIA_TOKEN=<token>` to launch pre-signed-in).

## File Structure (Phase 3B)

```
ios/Sources/
  App/AppModel.swift                 # MODIFY: persist + expose current username
  Storage/TokenStore.swift           # MODIFY: store username alongside token
  Features/Onboarding/OnboardingViewModel.swift  # MODIFY: pass username on sign-in
  Networking/
    LeaderboardEndpoints.swift       # NEW: ranking + summary + weekly + profiles + models
  Features/
    Ranks/RanksView.swift            # NEW
    Ranks/RanksViewModel.swift       # NEW
    Ranks/RankDetailView.swift       # NEW (podium + ranked list)
    Profile/ProfileView.swift        # NEW (You)
    Profile/ProfileViewModel.swift   # NEW
    Groups/GroupsView.swift          # NEW (coming soon)
    Shell/MainTabView.swift          # NEW: 4-tab coastal shell
  App/RootView.swift                 # MODIFY: signed-in -> MainTabView
ios/Tests/
    CurrentUserTests.swift           # NEW (username persistence)
    LeaderboardEndpointsTests.swift  # NEW
    RanksViewModelTests.swift        # NEW
    ProfileViewModelTests.swift      # NEW
```

---

### Task 1: Persist the current username

Deliverable: the app remembers the signed-in user's username (needed for the You tab and "You · #N"). TDD.

**Files:** Modify `ios/Sources/Storage/TokenStore.swift`, `ios/Sources/App/AppModel.swift`, `ios/Sources/Features/Onboarding/OnboardingViewModel.swift`; create `ios/Tests/CurrentUserTests.swift`.

**Interfaces:**
- `TokenStore` gains `func saveUsername(_:)`, `func loadUsername() -> String?`, and `clear()` also clears the username. `InMemoryTokenStore`/`KeychainTokenStore` both implement it.
- `AppModel`: `signIn(token:username:)` (username optional-defaulted for back-compat is NOT needed; update the one call site), `private(set) var username: String?`, set from the store on init.
- `OnboardingViewModel.join()` calls `onSignIn` with both token and username. Change the callback to `(_ token: String, _ username: String) -> Void` and update `RootView`/`SignedInView`/`MainTabView` call sites.

- [ ] **Step 1: Write failing tests `ios/Tests/CurrentUserTests.swift`** (subclass `XCTestCase`, `@MainActor` for the AppModel parts):

```swift
import XCTest
@testable import synzoia

final class CurrentUserStoreTests: XCTestCase {
    func testInMemoryStoresUsername() {
        let s = InMemoryTokenStore(nil)
        XCTAssertNil(s.loadUsername())
        s.saveUsername("micah")
        XCTAssertEqual(s.loadUsername(), "micah")
        s.clear()
        XCTAssertNil(s.loadUsername())
    }
}

@MainActor
final class AppModelUsernameTests: XCTestCase {
    func testSignInPersistsUsername() {
        let store = InMemoryTokenStore(nil)
        let model = AppModel(store: store)
        model.signIn(token: "TOK", username: "micah")
        XCTAssertEqual(model.username, "micah")
        XCTAssertEqual(store.loadUsername(), "micah")
    }
    func testStartsWithStoredUsername() {
        let store = InMemoryTokenStore("TOK"); store.saveUsername("angela")
        let model = AppModel(store: store)
        XCTAssertEqual(model.username, "angela")
    }
    func testSignOutClearsUsername() {
        let store = InMemoryTokenStore("TOK"); store.saveUsername("x")
        let model = AppModel(store: store)
        model.signOut()
        XCTAssertNil(model.username)
        XCTAssertNil(store.loadUsername())
    }
}
```

- [ ] **Step 2: Run -> RED.**
- [ ] **Step 3: Implement.** Add username storage to `TokenStore` (Keychain: a second `account = "username"` item in the same service; InMemory: a second stored var). Add `username` to `AppModel` (load on init, set in `signIn(token:username:)`, clear in `signOut`). Update `OnboardingViewModel` to call `onSignIn(profile.token, profile.username)` and change its `onSignIn` type. Update the `OnboardingView` initializer's `onSignIn` type and the call site in `RootView`/`SignedInView` (whichever passes the closure) to `app.signIn(token:username:)`.
- [ ] **Step 4: Run -> GREEN; build.**
- [ ] **Step 5: Commit** `feat(ios): persist current username for the profile tab`.

---

### Task 2: Leaderboard / summary / profiles endpoints

Deliverable: `APIClient` read methods + Codable models for ranking, user summaries, weekly, and profiles. TDD with recorded JSON.

**Files:** Create `ios/Sources/Networking/LeaderboardEndpoints.swift`, `ios/Tests/LeaderboardEndpointsTests.swift`.

**Interfaces (produced):**
- `struct RankEntry: Decodable, Equatable { let rank: Int; let username: String; let total: Int }`
- `struct DailyTotal: Decodable, Equatable { let date: String; let total: Int }`
- `struct RankingResponse: Decodable, Equatable { let weekStart: String; let weekEnd: String; let leaderboard: [RankEntry]; let dailyBreakdown: [DailyTotal] }` (ignore the differing `total_steps`/`total_minutes` top-level field by simply not declaring it)
- `struct BestEntry: Decodable, Equatable { let date: String; let total: Int }`
- `struct UserMetricSummary: Decodable, Equatable { let username: String; let joinDate: String?; let score: Int?; let rank: Int?; let best: BestEntry? }` with a custom decoder that reads `best_day` OR `best_night` into `best` (use `decodeIfPresent` for both keys).
- `struct UserWeekly: Decodable, Equatable { let username: String; let weeklyTotal: Int?; let rankThisWeek: Int?; let dailyBreakdown: [DailyTotal] }`
- `struct ProfileSummary: Decodable, Equatable { let username: String; let joinDate: String; let totalStepsAllTime: Int }` and `struct ProfilesResponse: Decodable { let profiles: [ProfileSummary] }`
- `enum Metric { case steps, sleep; var path: String { steps->"steps", sleep->"sleep" } }`
- `extension APIClient { func ranking(_ metric: Metric) async throws -> RankingResponse; func userSummary(_ metric: Metric, username: String) async throws -> UserMetricSummary; func userWeekly(_ metric: Metric, username: String) async throws -> UserWeekly; func profiles() async throws -> [ProfileSummary] }`

- [ ] **Step 1: Write failing tests `ios/Tests/LeaderboardEndpointsTests.swift`** (subclass `MockedNetworkTestCase`). Cover: steps ranking decodes leaderboard + daily_breakdown; a sleep summary with `best_night` decodes into `best`; a steps summary with `best_day` decodes into `best`; null `score`/`best`/`rank` decode as nil; profiles decode; each method hits the right path (`/api/steps/ranking`, `/api/sleep/users/alice/summary`, etc).

```swift
import XCTest
@testable import synzoia

final class LeaderboardEndpointsTests: MockedNetworkTestCase {
    private func client() -> APIClient {
        APIClient(config: APIConfig(baseURL: URL(string: "https://example.test")!),
                  session: MockURLProtocol.makeSession())
    }
    func testStepsRankingDecodes() async throws {
        MockURLProtocol.handler = { req in
            XCTAssertEqual(req.url?.path, "/api/steps/ranking")
            let body = Data(#"{"week_start":"2026-06-15","week_end":"2026-06-21","total_steps":1050000,"leaderboard":[{"rank":1,"username":"micah","total":412800}],"daily_breakdown":[{"date":"2026-06-15","total":8500}]}"#.utf8)
            return (MockURLProtocol.response(req, status: 200), body)
        }
        let r = try await client().ranking(.steps)
        XCTAssertEqual(r.leaderboard.first, RankEntry(rank: 1, username: "micah", total: 412800))
        XCTAssertEqual(r.dailyBreakdown.count, 1)
    }
    func testSleepSummaryBestNightDecodesIntoBest() async throws {
        MockURLProtocol.handler = { req in
            XCTAssertEqual(req.url?.path, "/api/sleep/users/angela/summary")
            let body = Data(#"{"username":"angela","join_date":"2026-01-15T09:30:00","score":103680,"best_night":{"date":"2026-03-10","total":720},"rank":1}"#.utf8)
            return (MockURLProtocol.response(req, status: 200), body)
        }
        let s = try await client().userSummary(.sleep, username: "angela")
        XCTAssertEqual(s.best, BestEntry(date: "2026-03-10", total: 720))
        XCTAssertEqual(s.rank, 1)
    }
    func testStepsSummaryNullsDecodeNil() async throws {
        MockURLProtocol.handler = { req in
            (MockURLProtocol.response(req, status: 200),
             Data(#"{"username":"new","join_date":"2026-06-01T00:00:00","score":null,"best_day":null,"rank":null}"#.utf8))
        }
        let s = try await client().userSummary(.steps, username: "new")
        XCTAssertNil(s.score); XCTAssertNil(s.best); XCTAssertNil(s.rank)
    }
    func testProfilesDecode() async throws {
        MockURLProtocol.handler = { req in
            XCTAssertEqual(req.url?.path, "/api/profiles")
            return (MockURLProtocol.response(req, status: 200),
                    Data(#"{"profiles":[{"username":"micah","join_date":"2026-01-01T00:00:00","total_steps_all_time":42000}]}"#.utf8))
        }
        let p = try await client().profiles()
        XCTAssertEqual(p.first?.username, "micah")
    }
}
```

- [ ] **Step 2: Run -> RED.**
- [ ] **Step 3: Implement `LeaderboardEndpoints.swift`.** Models as above. `UserMetricSummary` needs a manual `init(from:)` to map either `best_day` or `best_night` -> `best` (decode both with `decodeIfPresent`, take whichever is non-nil); note `.convertFromSnakeCase` turns the keys into `bestDay`/`bestNight`, so the `CodingKeys` are `bestDay`/`bestNight`. Endpoint methods build paths from `Metric.path`.
- [ ] **Step 4: Run -> GREEN; build.**
- [ ] **Step 5: Commit** `feat(ios): leaderboard, summary, and profiles endpoints`.

---

### Task 3: Ranks screen (steps + sleep grid)

Deliverable: the Ranks tab content: a grid of Steps and Sleep cards (design lines 167-202), each showing the leader and the current user's rank, tappable to the detail. View-model TDD; view build + screenshot.

**Files:** Create `ios/Sources/Features/Ranks/RanksViewModel.swift`, `ios/Sources/Features/Ranks/RanksView.swift`, `ios/Tests/RanksViewModelTests.swift`.

**Interfaces:** `@MainActor @Observable RanksViewModel { enum State; init(api:currentUsername:); func load() async; var steps: RankingResponse?; var sleep: RankingResponse? }` exposing for each metric the leader (leaderboard.first) and the current user's entry (first where username == currentUsername). `RanksView(api:currentUsername:onOpenDetail: (Metric)->Void)`.

- [ ] **Step 1: Failing `RanksViewModelTests`** asserting: after load with mocked steps+sleep ranking, `leader(.steps)` is the rank-1 entry and `myRank(.steps)` finds the current user (or nil if absent); a failed fetch -> `.failed`.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement vm** (fetch both rankings concurrently with `async let`; expose leader + myEntry helpers). Implement `RanksView`: header (serif "Leaderboard" + MonoLabel "Rolling 30 days · capped"); a 2-column grid (`LazyVGrid`) with a Steps card and a Sleep card matching design lines 176-186 (icon, mono category label, leader avatar+name+value, "You · #N" line). Format sleep totals as "Xh YYm avg" and steps as grouped integers. Tapping a card calls `onOpenDetail(metric)`.
- [ ] **Step 4: GREEN; build.**
- [ ] **Step 5: Screenshot** the Ranks tab (via the tab shell once Task 7 lands, or a temporary preview) to `/tmp/syn-ranks.png`; compare to design. (If the shell is not yet wired, defer the screenshot to Task 7 and just build-verify here.)
- [ ] **Step 6: Commit** `feat(ios): ranks leaderboard grid`.

---

### Task 4: Rank detail (podium + ranked list)

Deliverable: the rank detail screen (design lines 277-303): a Steps/Sleep segmented toggle, a top-3 podium, the ranked list with the current user highlighted, and the capped note. Build + screenshot.

**Files:** Create `ios/Sources/Features/Ranks/RankDetailView.swift`. (Reuses `RanksViewModel` data or fetches via `APIClient.ranking`.)

**Interfaces:** `RankDetailView(api:currentUsername:metric: Metric)` with an internal `@State` selected metric (defaulting to the passed one) and its own load of `ranking(metric)`.

- [ ] **Step 1: Implement** the podium (top 3 from `leaderboard`, center = #1 raised, amber ring), the ranked rows (#4+ with rank, avatar, @username, total; the current user's row highlighted in `SynColor.primary` 12% tint per design line 299), a segmented Steps/Sleep toggle styled like design lines 285-289 that reloads on change, and the capped note "Capped at 25k / day. Consistency beats one big day." (steps) / appropriate sleep note. Back button calls a passed `onBack` or uses `dismiss`.
- [ ] **Step 2: Build green; screenshot** to `/tmp/syn-rankdetail.png`; compare to design lines 277-303.
- [ ] **Step 3: Commit** `feat(ios): rank detail with podium and ranked list`.

---

### Task 5: Profile / You screen

Deliverable: the You tab (design lines 204-247): cover gradient + avatar + handle + joined/score, the steps 30-day-score and rank cards, a Today card with the 7-day `WeekBars`, and an "Apple Health connected" row that opens Settings. View-model TDD; view build + screenshot. (Omit the unbacked "day streak".)

**Files:** Create `ios/Sources/Features/Profile/ProfileViewModel.swift`, `ios/Sources/Features/Profile/ProfileView.swift`, `ios/Tests/ProfileViewModelTests.swift`.

**Interfaces:** `@MainActor @Observable ProfileViewModel { init(api:username:); func load() async; var stepsSummary: UserMetricSummary?; var stepsWeekly: UserWeekly? }`. `ProfileView(api:username:onOpenSettings: ()->Void)`.

- [ ] **Step 1: Failing `ProfileViewModelTests`** asserting load populates `stepsSummary` (score/rank) and `stepsWeekly` (dailyBreakdown for the bars); failed fetch -> `.failed`; nil score/rank handled.
- [ ] **Step 2: RED.**
- [ ] **Step 3: Implement vm** (fetch steps summary + weekly via `async let`). Implement `ProfileView`: cover gradient header (design line 207), large avatar (`GradientAvatar(username:size:78)`) + serif "@username" + mono "JOINED <month year> · <score> STEPS" (from summary/profiles `join_date`); a 2-card row (30-day score, Rank #N from summary); a Today/this-week card containing `WeekBars(values:)` built from `stepsWeekly.dailyBreakdown` (normalize totals to 0...1); an "Apple Health connected" row (primary-tinted, heart) that calls `onOpenSettings`. Omit the day-streak (no backend). Read design lines 204-247.
- [ ] **Step 4: GREEN; build; screenshot** to `/tmp/syn-profile.png`; compare to design.
- [ ] **Step 5: Commit** `feat(ios): profile (You) screen`.

---

### Task 6: Groups coming-soon screen

Deliverable: a styled Groups placeholder (uses the design's group-card visual language) that clearly says groups are coming. Build + screenshot.

**Files:** Create `ios/Sources/Features/Groups/GroupsView.swift`.

- [ ] **Step 1: Implement `GroupsView`:** header (serif "Groups" + MonoLabel "Your circles"); a centered coastal empty-state: a `ContentUnavailableView`-style block or a styled `SynCard` with a people icon, a serif "Groups are coming" line, and muted body "Crews, challenges, and circles are on the way. For now everyone shares one feed and leaderboard." Keep it visually on-brand (design lines 120-164 for the group-card look, but rendered as a coming-soon state, not real groups).
- [ ] **Step 2: Build green; screenshot** to `/tmp/syn-groups.png`.
- [ ] **Step 3: Commit** `feat(ios): groups coming-soon screen`.

---

### Task 7: 4-tab shell

Deliverable: a coastal tab bar (Feed / Groups / Ranks / You) replacing the Feed-only root; Settings reachable from the You tab; auto-sync preserved. Build + screenshot of the tab bar.

**Files:** Create `ios/Sources/Features/Shell/MainTabView.swift`; modify `ios/Sources/App/RootView.swift` (signed-in -> `MainTabView`); the existing `SignedInView` is either replaced by `MainTabView` or `MainTabView` absorbs its SyncEngine ownership + the `.task` auto-sync.

- [ ] **Step 1: Implement `MainTabView`:** owns the `SyncEngine` (built with `HealthKitReader()` + `app.authedClient()`, as `SignedInView` did) and runs `requestPermission` + `syncNow` in `.task`. A `TabView` (or a custom bottom bar matching design lines 397-416: blur background, top border, 4 items each an icon + label, active = `SynColor.primary`, idle = `SynColor.muted`). Tabs: Feed = the restyled `FeedView(api: app.api, onOpenSettings: openSettings)`; Groups = `GroupsView()`; Ranks = `RanksView(api: app.api, currentUsername: app.username, onOpenDetail:)` wrapped in a `NavigationStack` pushing `RankDetailView`; You = `ProfileView(api: app.api, username: app.username ?? "", onOpenSettings: openSettings)`. A `.sheet` presents `SettingsView(sync:app:)`. Use SF Symbols approximating the design tab icons (Feed: `dot.radiowaves.up.forward` or `wave.3.forward`; Groups: `person.2`; Ranks: `trophy`; You: `person.crop.circle`). If a custom bar is too involved, a styled `TabView` with `.tint(SynColor.primary)` and a configured `UITabBarAppearance` (dark, blur) is acceptable as long as it reads like the design.
- [ ] **Step 2: Update `RootView`** signed-in branch to `MainTabView(app: app)`.
- [ ] **Step 3: Regenerate; build green; full suite green.**
- [ ] **Step 4: Screenshot** the app on each tab (launch pre-signed-in via `SIMCTL_CHILD_SYNZOIA_TOKEN`); save `/tmp/syn-tab-feed.png`, `/tmp/syn-tab-ranks.png`, `/tmp/syn-tab-you.png`, `/tmp/syn-tab-groups.png`. Compare the tab bar + each tab to the design.
- [ ] **Step 5: Commit** `feat(ios): 4-tab coastal shell`.

---

### Task 8: Phase 3 verification + whole-branch review

- [ ] **Step 1:** Full suite green (count grows with the new view-model/endpoint tests).
- [ ] **Step 2:** Confirm the screenshot set covers Feed, Ranks, Rank detail, Profile, Groups, Settings and each matches the design.
- [ ] **Step 3:** This is the end of Phase 3. The controller dispatches the whole-branch code review over the full Phase 3 range (3A start `08de880`..HEAD) on the most capable model, triaging the accumulated Minor findings (WeekBars highlightLast, PostRow size, SynFont PJS names, SleepStageBar approximations). Fix Critical/Important; record the rest.
- [ ] **Step 4:** No commit (verification). Report the screenshot set + review verdict.

## Self-Review

**Spec coverage:** username persistence (T1, unblocks You + "You · #N"); endpoints (T2); Ranks grid (T3) + detail (T4); Profile/You (T5); Groups coming-soon (T6); 4-tab shell + Settings relocation + auto-sync (T7); verification + whole-branch review (T8). Steps + Sleep only for Ranks; Groups is a placeholder; reactions/comments and Workouts/Calories remain out of scope per the approved decisions. Day-streak omitted (no backend).

**Placeholder scan:** screen tasks delegate exact pixel values to the design source with line ranges (faithful-implementation instruction, not a TBD). Endpoint contracts and all test JSON are concrete. `best_day`/`best_night` divergence handled explicitly in T2.

**Type consistency:** `TokenStore.saveUsername/loadUsername`, `AppModel.signIn(token:username:)`/`username`, `OnboardingViewModel` `onSignIn(token,username)`, `Metric`, `RankEntry`/`RankingResponse`/`UserMetricSummary`/`BestEntry`/`UserWeekly`/`ProfileSummary`, `APIClient.ranking/userSummary/userWeekly/profiles`, `RanksViewModel`/`RanksView`, `RankDetailView`, `ProfileViewModel`/`ProfileView`, `GroupsView`, `MainTabView` are defined and consumed consistently across tasks. `MainTabView` consumes every screen built in T3-T6.
