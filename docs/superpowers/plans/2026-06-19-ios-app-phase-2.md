# synzoia iOS app: Phase 2 Implementation Plan (Apple Health sleep + steps sync)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The app reads Apple Health and posts last night's sleep and today's steps to the existing backend: a permission prompt, a `SyncEngine`, a manual "Sync now" Settings screen, and auto-sync on launch. First run on a real iPhone.

**Architecture:** A pure, HealthKit-free mapping layer (`SleepSample` DTO -> exact newline-joined `POST /api/sleep` body; today's step total -> `POST /api/steps` body) sits behind a `HealthReading` protocol. The real `HealthKitReader` is the only file importing HealthKit (build-verified, device-tested by the human); a `FakeHealthReader` drives unit tests. `SyncEngine` (an `@MainActor @Observable`) orchestrates read -> build -> post -> status, fully unit-tested with the fake reader and a mocked network. A Settings sheet (reached from a Feed toolbar button) shows permission state, a Sync-now button, last-sync result, and the token.

**Tech Stack:** Swift (language mode 5), SwiftUI, HealthKit (one file only), Observation, URLSession, XCTest, XcodeGen. No third-party Swift packages.

**Scope note:** This is Phase 2 from `docs/superpowers/specs/2026-06-18-ios-app-design.md`, extended to also cover the (small) steps *sync* alongside sleep (the steps *screens* stay in Phase 3). Background auto-sync stays in Phase 4. Builds on Phase 0+1 (branch `feat/ios-app`, HEAD `3848a12`). The full verified backend contract with file:line proof is in `sdd/phase2-healthkit-contract.md` (git-excluded working reference); the load-bearing facts are embedded below so this plan is self-contained.

## Global Constraints

Every task implicitly includes these. Values are copied from the spec and the adversarially-verified Phase 2 contract.

- **Platform/language:** iOS 17.0 target; Swift language mode 5.0; iPhone only. Apple frameworks only, NO SPM.
- **Worktree/branch:** work in `~/Developer/synzoia/.claude/worktrees/ios-app` on branch `feat/ios-app`. Paths below are relative to that root. After adding/removing files or editing `ios/project.yml`, run `cd ios && xcodegen generate && cd ..` (XcodeGen snapshots the file list at generate time).
- **Production base URL:** `https://synzoia.vercel.app`. Reads public; `POST /api/sleep` and `POST /api/steps` require the `Bearer` token (use `AppModel.authedClient()`).
- **JSON:** existing `APIClient.decoder`/`.encoder` use `.convertFromSnakeCase` / `.convertToSnakeCase`. All Phase 2 wire field names are single words (`values`, `starts`, `ends`, `types`, `duration`, `timestamp`, `total`), so snake conversion is a no-op for the request bodies; response fields like `session_type` decode to `sessionType`.
- **Sleep wire contract (verified, byte-for-byte):**
  - `POST /api/sleep` body is `{values, starts, ends, types, duration, timestamp}`, all strings. The first five are newline (`\n`) joined, index-aligned, EQUAL length, NO trailing newline.
  - **Stages go in `values`** (case-sensitive, exactly one of `Core` / `Deep` / `REM` / `Awake`). Unrecognized values are silently dropped from totals (no error), so emit ONLY those four.
  - **`types` is ignored by the backend** (parsed for length only); emit the literal `Sleep` once per row to match the existing Shortcut.
  - `duration[i]` is the per-sample length and is the SOLE source of the backend's minute totals. Emit **bare integer seconds** = `Int(endDate.timeIntervalSince(startDate))` computed from the real second-precision HealthKit dates (NOT from the minute-truncated wall-clock strings).
  - `starts[i]` / `ends[i]` are wall-clock strings formatted `"MMM d, yyyy 'at' h:mm a"` (e.g. `Jun 18, 2026 at 11:30 PM`), locale `en_US_POSIX`, the device's current time zone, no seconds.
  - `timestamp` is a single ISO-8601 string WITH an explicit UTC offset (e.g. `2026-06-19T09:00:00-05:00`), no `Z`. The offset is mandatory (a naive timestamp is a 422). Format `"yyyy-MM-dd'T'HH:mm:ssXXX"`, `en_US_POSIX`, device zone.
- **HealthKit sleep stage mapping (HKCategoryValueSleepAnalysis raw Int -> `values` string, or drop):** `0` inBed -> DROP; `1` asleep(legacy) -> `Core`; `2` awake -> `Awake`; `3` asleepUnspecified -> `Core`; `4` asleepCore -> `Core`; `5` asleepDeep -> `Deep`; `6` asleepREM -> `REM`.
- **Steps wire contract (verified):** `POST /api/steps` body is `{timestamp, total}` where `timestamp` is ISO-8601 with offset and `total` is the day's cumulative step count (Int >= 0). Backend keeps MAX per Central-Time day, so re-posting a cumulative total is idempotent. Read today's total with `HKStatisticsQuery` `.cumulativeSum` over `[startOfDay(device-local), now]` in `HKUnit.count()`.
- **HealthKit read-auth is opaque:** a denied read returns an empty array with no error, indistinguishable from "no data". Never render an "access denied" state from empty results; show "no new data" and point at Settings > Health.
- **Writing rule:** no em dashes anywhere (code, comments, strings, commits, docs). Use colons, commas, or parentheses.
- **Commits:** present-tense subject; end every commit body with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Test simulator:** `iPhone 17`. Test/build command shape: `xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia -destination 'platform=iOS Simulator,name=iPhone 17' <build|test>`.

## File Structure (Phase 2 additions)

```
ios/
  Sources/
    synzoia.entitlements              # NEW: HealthKit entitlement
    Info.plist                        # MODIFY: add NSHealthShareUsageDescription
    Health/
      SleepSample.swift               # NEW: DTO (no HealthKit import)
      SleepStageMapping.swift         # NEW: pure mapSleepStage(hkRawValue:)
      HealthPayloadBuilder.swift      # NEW: pure builders -> wire bodies
      HealthReading.swift             # NEW: protocol (no HealthKit import)
      HealthKitReader.swift           # NEW: real impl (ONLY HealthKit import)
      SyncEngine.swift                # NEW: @MainActor @Observable orchestrator
    Networking/
      HealthEndpoints.swift           # NEW: postSleep / postSteps + response models
    Features/
      Feed/FeedView.swift             # MODIFY: optional settings toolbar button
      Settings/SettingsView.swift     # NEW
      Settings/SignedInView.swift     # NEW: owns SyncEngine, hosts Feed + Settings sheet
    App/RootView.swift                # MODIFY: signed-in branch shows SignedInView
  project.yml                         # MODIFY: CODE_SIGN_ENTITLEMENTS on app target
  Tests/
    SleepStageMappingTests.swift      # NEW
    HealthPayloadBuilderTests.swift   # NEW
    HealthEndpointsTests.swift        # NEW
    FakeHealthReader.swift            # NEW: test double
    SyncEngineTests.swift             # NEW
```

---

### Task 1: HealthKit project configuration

Deliverable: the HealthKit entitlement, Info.plist usage string, and project.yml wiring are in place; the simulator build and existing 21 tests still pass (simulator builds do not enforce the device entitlement).

**Files:**
- Create: `ios/Sources/synzoia.entitlements`
- Modify: `ios/Sources/Info.plist`
- Modify: `ios/project.yml`

**Interfaces:** Produces no Swift symbols; enables HealthKit for later tasks.

- [ ] **Step 1: Create `ios/Sources/synzoia.entitlements`.**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.developer.healthkit</key>
    <true/>
    <key>com.apple.developer.healthkit.access</key>
    <array/>
</dict>
</plist>
```

- [ ] **Step 2: Add `NSHealthShareUsageDescription` to `ios/Sources/Info.plist`** (inside the top-level `<dict>`, before its closing `</dict>`).

```xml
  <key>NSHealthShareUsageDescription</key>
  <string>synzoia reads your sleep and step data from Apple Health to post your nightly sleep and daily steps to your crew feed and leaderboard.</string>
```

- [ ] **Step 3: Add the entitlements setting to the `synzoia` app target in `ios/project.yml`.** In the `synzoia` target's `settings.base` block (the one with `INFOPLIST_FILE`, `PRODUCT_BUNDLE_IDENTIFIER`, etc.), add this line. Do NOT add it to `synzoiaTests`.

```yaml
        CODE_SIGN_ENTITLEMENTS: Sources/synzoia.entitlements
```

- [ ] **Step 4: Regenerate and build for the simulator.**

```bash
cd ios && xcodegen generate && cd ..
xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
```

Expected: `** BUILD SUCCEEDED **`. (Simulator builds set `CODE_SIGNING_ALLOWED=NO`, so the HealthKit entitlement does not require a provisioning profile here; the device profile is the human's Xcode step in Task 8. If the build fails specifically on code signing, report it.)

- [ ] **Step 5: Run the existing suite to confirm no regression.**

```bash
xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia \
  -destination 'platform=iOS Simulator,name=iPhone 17' test
```

Expected: `** TEST SUCCEEDED **`, 21 tests.

- [ ] **Step 6: Commit.**

```bash
git add ios/project.yml ios/Sources/synzoia.entitlements ios/Sources/Info.plist
git commit -m "feat(ios): add HealthKit entitlement and usage description"
```

---

### Task 2: Sleep sample DTO and stage mapping

Deliverable: a HealthKit-free `SleepSample` DTO and a pure `mapSleepStage(hkRawValue:)` covering the full mapping table. TDD.

**Files:**
- Create: `ios/Sources/Health/SleepSample.swift`
- Create: `ios/Sources/Health/SleepStageMapping.swift`
- Create: `ios/Tests/SleepStageMappingTests.swift`

**Interfaces:**
- Produces:
  - `struct SleepSample: Equatable { enum Stage: String { case core="Core", deep="Deep", rem="REM", awake="Awake" }; let startDate: Date; let endDate: Date; let stage: Stage }`
  - `func mapSleepStage(hkRawValue: Int) -> SleepSample.Stage?`

- [ ] **Step 1: Write the failing tests `ios/Tests/SleepStageMappingTests.swift`.**

```swift
import XCTest
@testable import synzoia

final class SleepStageMappingTests: XCTestCase {
    func testMappingTable() {
        XCTAssertNil(mapSleepStage(hkRawValue: 0))               // inBed -> drop
        XCTAssertEqual(mapSleepStage(hkRawValue: 1), .core)      // asleep (legacy)
        XCTAssertEqual(mapSleepStage(hkRawValue: 2), .awake)     // awake
        XCTAssertEqual(mapSleepStage(hkRawValue: 3), .core)      // asleepUnspecified
        XCTAssertEqual(mapSleepStage(hkRawValue: 4), .core)      // asleepCore
        XCTAssertEqual(mapSleepStage(hkRawValue: 5), .deep)      // asleepDeep
        XCTAssertEqual(mapSleepStage(hkRawValue: 6), .rem)       // asleepREM
        XCTAssertNil(mapSleepStage(hkRawValue: 99))              // unknown -> drop
    }

    func testStageRawValuesAreBackendVocabulary() {
        XCTAssertEqual(SleepSample.Stage.core.rawValue, "Core")
        XCTAssertEqual(SleepSample.Stage.deep.rawValue, "Deep")
        XCTAssertEqual(SleepSample.Stage.rem.rawValue, "REM")
        XCTAssertEqual(SleepSample.Stage.awake.rawValue, "Awake")
    }
}
```

- [ ] **Step 2: Run to verify failure.** Expected: "Cannot find 'mapSleepStage' in scope" / "Cannot find 'SleepSample' in scope".

- [ ] **Step 3: Write `ios/Sources/Health/SleepSample.swift`.**

```swift
import Foundation

/// A sleep segment, decoupled from HealthKit so the mapping/build logic is
/// pure and unit-testable without constructing HKSample objects.
struct SleepSample: Equatable {
    /// Backend `values` vocabulary. The rawValue is the exact, case-sensitive
    /// string the server matches against (Core/Deep/REM/Awake).
    enum Stage: String, Equatable {
        case core = "Core"
        case deep = "Deep"
        case rem = "REM"
        case awake = "Awake"
    }

    let startDate: Date
    let endDate: Date
    let stage: Stage
}
```

- [ ] **Step 4: Write `ios/Sources/Health/SleepStageMapping.swift`.**

```swift
import Foundation

/// Maps an HKCategoryValueSleepAnalysis raw value to a backend stage, or nil
/// to drop the sample (inBed envelopes overlap the staged segments; unknown
/// values are not in the backend vocabulary and would be silently discarded).
func mapSleepStage(hkRawValue: Int) -> SleepSample.Stage? {
    switch hkRawValue {
    case 0: return nil          // inBed
    case 1: return .core        // asleep (legacy catch-all)
    case 2: return .awake       // awake
    case 3: return .core        // asleepUnspecified
    case 4: return .core        // asleepCore
    case 5: return .deep        // asleepDeep
    case 6: return .rem         // asleepREM
    default: return nil
    }
}
```

- [ ] **Step 5: Regenerate, run tests, verify pass.**

```bash
cd ios && xcodegen generate && cd ..
xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia \
  -destination 'platform=iOS Simulator,name=iPhone 17' test
```

Expected: `SleepStageMappingTests` pass.

- [ ] **Step 6: Commit.**

```bash
git add ios/Sources/Health/SleepSample.swift ios/Sources/Health/SleepStageMapping.swift ios/Tests/SleepStageMappingTests.swift
git commit -m "feat(ios): sleep sample DTO and HealthKit stage mapping"
```

---

### Task 3: Pure payload builders

Deliverable: pure functions that turn samples / a step total into the exact wire bodies, tested with the verified worked examples byte-for-byte. TDD.

**Files:**
- Create: `ios/Sources/Health/HealthPayloadBuilder.swift`
- Create: `ios/Tests/HealthPayloadBuilderTests.swift`

**Interfaces:**
- Produces:
  - `struct SleepPayload: Encodable, Equatable { let values, starts, ends, types, duration, timestamp: String }`
  - `enum HealthPayloadBuilder { static func buildSleepPayload(from: [SleepSample], capturedAt: Date, zone: TimeZone) -> SleepPayload; static func buildSteps(total: Int, capturedAt: Date, zone: TimeZone) -> (timestamp: String, total: Int) }`

- [ ] **Step 1: Write the failing tests `ios/Tests/HealthPayloadBuilderTests.swift`.** The expectations mirror the verified worked example (durations are bare seconds computed from real second-precision dates; wall-clock strings drop seconds).

```swift
import XCTest
@testable import synzoia

final class HealthPayloadBuilderTests: XCTestCase {
    // America/Chicago is CDT (-05:00) on 2026-06-18/19.
    private let zone = TimeZone(identifier: "America/Chicago")!

    /// Build a Date at a wall-clock instant in `zone`.
    private func date(_ y: Int, _ mo: Int, _ d: Int, _ h: Int, _ mi: Int, _ s: Int) -> Date {
        var c = DateComponents()
        c.year = y; c.month = mo; c.day = d; c.hour = h; c.minute = mi; c.second = s
        c.timeZone = zone
        return Calendar(identifier: .gregorian).date(from: c)!
    }

    func testBuildsExactWorkedExampleBody() {
        let samples = [
            SleepSample(startDate: date(2026, 6, 18, 23, 30, 0),
                        endDate:   date(2026, 6, 19, 0, 14, 1), stage: .deep),   // 2641s
            SleepSample(startDate: date(2026, 6, 19, 0, 14, 1),
                        endDate:   date(2026, 6, 19, 0, 14, 31), stage: .awake), // 30s
            SleepSample(startDate: date(2026, 6, 19, 0, 14, 31),
                        endDate:   date(2026, 6, 19, 6, 30, 0), stage: .core),   // 22529s
        ]
        let captured = date(2026, 6, 19, 9, 0, 0)
        let p = HealthPayloadBuilder.buildSleepPayload(from: samples, capturedAt: captured, zone: zone)

        XCTAssertEqual(p.values, "Deep\nAwake\nCore")
        XCTAssertEqual(p.types, "Sleep\nSleep\nSleep")
        XCTAssertEqual(p.starts, "Jun 18, 2026 at 11:30 PM\nJun 19, 2026 at 12:14 AM\nJun 19, 2026 at 12:14 AM")
        XCTAssertEqual(p.ends, "Jun 19, 2026 at 12:14 AM\nJun 19, 2026 at 12:14 AM\nJun 19, 2026 at 6:30 AM")
        XCTAssertEqual(p.duration, "2641\n30\n22529")
        XCTAssertEqual(p.timestamp, "2026-06-19T09:00:00-05:00")
    }

    func testSortsSamplesByStartAndHasNoTrailingNewline() {
        let samples = [
            SleepSample(startDate: date(2026, 6, 19, 0, 14, 31), endDate: date(2026, 6, 19, 6, 30, 0), stage: .core),
            SleepSample(startDate: date(2026, 6, 18, 23, 30, 0), endDate: date(2026, 6, 19, 0, 14, 0), stage: .deep),
        ]
        let p = HealthPayloadBuilder.buildSleepPayload(from: samples, capturedAt: date(2026, 6, 19, 9, 0, 0), zone: zone)
        XCTAssertEqual(p.values, "Deep\nCore")           // re-sorted by start
        XCTAssertFalse(p.values.hasSuffix("\n"))
        XCTAssertFalse(p.duration.hasSuffix("\n"))
        // equal element counts across all five arrays
        let counts = [p.values, p.starts, p.ends, p.types, p.duration].map { $0.split(separator: "\n", omittingEmptySubsequences: false).count }
        XCTAssertEqual(Set(counts).count, 1)
    }

    func testBuildStepsWithOffset() {
        let steps = HealthPayloadBuilder.buildSteps(total: 8432, capturedAt: date(2026, 6, 19, 9, 0, 0), zone: zone)
        XCTAssertEqual(steps.timestamp, "2026-06-19T09:00:00-05:00")
        XCTAssertEqual(steps.total, 8432)
    }
}
```

- [ ] **Step 2: Run to verify failure.** Expected: "Cannot find 'HealthPayloadBuilder' in scope" / "Cannot find 'SleepPayload' in scope".

- [ ] **Step 3: Write `ios/Sources/Health/HealthPayloadBuilder.swift`.**

```swift
import Foundation

/// Matches the backend IngestSleepRequest body. Field names are the wire
/// names (single words, unaffected by snake_case conversion).
struct SleepPayload: Encodable, Equatable {
    let values: String
    let starts: String
    let ends: String
    let types: String
    let duration: String
    let timestamp: String
}

enum HealthPayloadBuilder {
    /// Wall-clock formatter for starts/ends: "Jun 18, 2026 at 11:30 PM".
    /// en_US_POSIX + the device zone, no seconds. The backend zero-pads
    /// day/hour itself, so non-padded output is accepted.
    private static func wallClock(_ zone: TimeZone) -> DateFormatter {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = zone
        f.dateFormat = "MMM d, yyyy 'at' h:mm a"
        return f
    }

    /// ISO-8601 with an explicit offset (mandatory): "2026-06-19T09:00:00-05:00".
    private static func isoWithOffset(_ date: Date, _ zone: TimeZone) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = zone
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ssXXX"
        return f.string(from: date)
    }

    static func buildSleepPayload(from samples: [SleepSample], capturedAt: Date, zone: TimeZone) -> SleepPayload {
        let sorted = samples.sorted { $0.startDate < $1.startDate }
        let wc = wallClock(zone)
        return SleepPayload(
            values: sorted.map { $0.stage.rawValue }.joined(separator: "\n"),
            starts: sorted.map { wc.string(from: $0.startDate) }.joined(separator: "\n"),
            ends: sorted.map { wc.string(from: $0.endDate) }.joined(separator: "\n"),
            types: sorted.map { _ in "Sleep" }.joined(separator: "\n"),
            // Duration is the backend's sole source of minute totals. Compute it
            // from the real second-precision dates, not the truncated wall clock.
            duration: sorted.map { String(Int($0.endDate.timeIntervalSince($0.startDate))) }.joined(separator: "\n"),
            timestamp: isoWithOffset(capturedAt, zone)
        )
    }

    static func buildSteps(total: Int, capturedAt: Date, zone: TimeZone) -> (timestamp: String, total: Int) {
        (timestamp: isoWithOffset(capturedAt, zone), total: total)
    }
}
```

- [ ] **Step 4: Run tests, verify pass.** Expected: `HealthPayloadBuilderTests` pass. If the wall-clock or ISO strings differ, fix the format string before proceeding (these strings are the contract).

- [ ] **Step 5: Commit.**

```bash
git add ios/Sources/Health/HealthPayloadBuilder.swift ios/Tests/HealthPayloadBuilderTests.swift
git commit -m "feat(ios): pure builders for sleep and steps wire payloads"
```

---

### Task 4: Sleep/steps POST endpoints and response models

Deliverable: `postSleep` and `postSteps` on `APIClient`, with the response models, tested against a mocked network. TDD.

**Files:**
- Create: `ios/Sources/Networking/HealthEndpoints.swift`
- Create: `ios/Tests/HealthEndpointsTests.swift`

**Interfaces:**
- Consumes: `APIClient.post`, `SleepPayload`, `MockURLProtocol`.
- Produces:
  - `struct SleepSession: Decodable, Equatable { let id, userId: Int; let sessionType, status: String; let reviewFlag: Bool; let sleepDate, onset, wake: String; let timeInBedMin, totalAsleepMin, awakeMin, coreMin, deepMin, remMin, wakeups: Int; let efficiency: Double; let capturedAt: String }`
  - `struct IngestSleepResponse: Decodable, Equatable { let sessions: [SleepSession] }`
  - `struct CreateStepRequest: Encodable { let timestamp: String; let total: Int }`
  - `struct CreateStepResponse: Decodable, Equatable { let id, userId: Int; let timestamp: String; let total: Int }`
  - `extension APIClient { func postSleep(_ payload: SleepPayload) async throws -> [SleepSession]; func postSteps(timestamp: String, total: Int) async throws -> CreateStepResponse }`

- [ ] **Step 1: Write the failing tests `ios/Tests/HealthEndpointsTests.swift`.** Response JSON literals are copied from the verified contract.

```swift
import XCTest
@testable import synzoia

final class HealthEndpointsTests: MockedNetworkTestCase {
    private func client() -> APIClient {
        APIClient(config: APIConfig(baseURL: URL(string: "https://example.test")!),
                  session: MockURLProtocol.makeSession(), token: "TOK")
    }

    func testPostSleepHitsEndpointWithBearerAndDecodesSession() async throws {
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/sleep")
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer TOK")
            let body = Data(#"""
            {"sessions":[{"id":789,"user_id":45,"session_type":"night","status":"final","review_flag":false,
            "sleep_date":"2026-06-18","onset":"2026-06-18T23:30:00","wake":"2026-06-19T06:30:00",
            "time_in_bed_min":420,"total_asleep_min":419,"awake_min":0,"core_min":375,"deep_min":44,"rem_min":0,
            "wakeups":0,"efficiency":0.9976,"captured_at":"2026-06-19T09:00:00"}]}
            """#.utf8)
            return (MockURLProtocol.response(request, status: 201), body)
        }
        let payload = SleepPayload(values: "Core", starts: "Jun 18, 2026 at 11:30 PM",
                                   ends: "Jun 19, 2026 at 6:30 AM", types: "Sleep",
                                   duration: "25200", timestamp: "2026-06-19T09:00:00-05:00")
        let sessions = try await client().postSleep(payload)
        XCTAssertEqual(sessions.count, 1)
        XCTAssertEqual(sessions.first?.sessionType, "night")
        XCTAssertEqual(sessions.first?.totalAsleepMin, 419)
    }

    func testPostStepsSendsBodyAndDecodes() async throws {
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/steps")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer TOK")
            let body = Data(#"{"id":1,"user_id":45,"timestamp":"2026-06-19T09:00:00","total":8432}"#.utf8)
            return (MockURLProtocol.response(request, status: 201), body)
        }
        let r = try await client().postSteps(timestamp: "2026-06-19T09:00:00-05:00", total: 8432)
        XCTAssertEqual(r.total, 8432)
    }

    func testPostSleepSurfacesValidationError() async {
        MockURLProtocol.handler = { request in
            let body = Data(#"{"error":{"code":"invalid_payload","message":"Mismatched array lengths."}}"#.utf8)
            return (MockURLProtocol.response(request, status: 422), body)
        }
        let payload = SleepPayload(values: "Core", starts: "x", ends: "y", types: "Sleep", duration: "1", timestamp: "t")
        do {
            _ = try await client().postSleep(payload)
            XCTFail("expected error")
        } catch let error as APIError {
            XCTAssertEqual(error, .http(status: 422, code: "invalid_payload", message: "Mismatched array lengths."))
        }
    }
}
```

- [ ] **Step 2: Run to verify failure.** Expected: "Value of type 'APIClient' has no member 'postSleep'" / "Cannot find 'SleepSession' in scope".

- [ ] **Step 3: Write `ios/Sources/Networking/HealthEndpoints.swift`.**

```swift
import Foundation

struct SleepSession: Decodable, Equatable {
    let id: Int
    let userId: Int
    let sessionType: String
    let status: String
    let reviewFlag: Bool
    let sleepDate: String
    let onset: String
    let wake: String
    let timeInBedMin: Int
    let totalAsleepMin: Int
    let awakeMin: Int
    let coreMin: Int
    let deepMin: Int
    let remMin: Int
    let wakeups: Int
    let efficiency: Double
    let capturedAt: String
}

struct IngestSleepResponse: Decodable, Equatable {
    let sessions: [SleepSession]
}

struct CreateStepRequest: Encodable {
    let timestamp: String
    let total: Int
}

struct CreateStepResponse: Decodable, Equatable {
    let id: Int
    let userId: Int
    let timestamp: String
    let total: Int
}

extension APIClient {
    /// Posts a raw sleep sample window. Returns the persisted sessions (the
    /// backend returns only the single latest session, but that is enough to
    /// confirm success).
    func postSleep(_ payload: SleepPayload) async throws -> [SleepSession] {
        let response: IngestSleepResponse = try await post("/api/sleep", body: payload)
        return response.sessions
    }

    /// Posts today's cumulative step total. Backend keeps MAX per CT day, so
    /// re-posting is idempotent.
    func postSteps(timestamp: String, total: Int) async throws -> CreateStepResponse {
        try await post("/api/steps", body: CreateStepRequest(timestamp: timestamp, total: total))
    }
}
```

- [ ] **Step 4: Run tests, verify pass.** Expected: `HealthEndpointsTests` pass.

- [ ] **Step 5: Commit.**

```bash
git add ios/Sources/Networking/HealthEndpoints.swift ios/Tests/HealthEndpointsTests.swift
git commit -m "feat(ios): postSleep and postSteps endpoints with response models"
```

---

### Task 5: HealthReading protocol, HealthKit reader, and test fake

Deliverable: the `HealthReading` seam, the real `HealthKitReader` (the only file importing HealthKit, build-verified here, device-verified in Task 8), and a `FakeHealthReader` for tests.

**Files:**
- Create: `ios/Sources/Health/HealthReading.swift`
- Create: `ios/Sources/Health/HealthKitReader.swift`
- Create: `ios/Tests/FakeHealthReader.swift`

**Interfaces:**
- Consumes: `SleepSample`, `mapSleepStage`.
- Produces:
  - `protocol HealthReading { func requestAuthorization() async throws; func fetchSleepSamples(from: Date, to: Date) async throws -> [SleepSample]; func fetchTodayStepTotal() async throws -> Int }`
  - `final class HealthKitReader: HealthReading` (real)
  - `final class FakeHealthReader: HealthReading` (test target) with settable `sleepSamples`, `stepTotal`, `error`, and recorded `authorizationRequested`.

- [ ] **Step 1: Write `ios/Sources/Health/HealthReading.swift`.** (No HealthKit import; pure seam.)

```swift
import Foundation

/// The app's read-only view of Apple Health. Abstracted so the orchestration
/// (SyncEngine) is unit-testable with a fake, and only one file imports HealthKit.
protocol HealthReading {
    func requestAuthorization() async throws
    func fetchSleepSamples(from start: Date, to end: Date) async throws -> [SleepSample]
    func fetchTodayStepTotal() async throws -> Int
}
```

- [ ] **Step 2: Write `ios/Sources/Health/HealthKitReader.swift`.** (The ONLY file importing HealthKit.)

```swift
import Foundation
import HealthKit

/// Real HealthKit-backed reader. Not unit-tested (requires a device with
/// Health data); verified on device in Task 8. The sample -> SleepSample
/// translation reuses the unit-tested mapSleepStage.
final class HealthKitReader: HealthReading {
    private let store = HKHealthStore()

    private var sleepType: HKCategoryType { HKObjectType.categoryType(forIdentifier: .sleepAnalysis)! }
    private var stepType: HKQuantityType { HKQuantityType(.stepCount) }

    func requestAuthorization() async throws {
        guard HKHealthStore.isHealthDataAvailable() else { return }
        try await store.requestAuthorization(toShare: [], read: [sleepType, stepType])
    }

    func fetchSleepSamples(from start: Date, to end: Date) async throws -> [SleepSample] {
        guard HKHealthStore.isHealthDataAvailable() else { return [] }
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: [])
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.sample(type: sleepType, predicate: predicate)],
            sortDescriptors: [SortDescriptor(\.startDate)]
        )
        let results = try await descriptor.result(for: store)
        return results.compactMap { sample -> SleepSample? in
            guard let cat = sample as? HKCategorySample,
                  let stage = mapSleepStage(hkRawValue: cat.value) else { return nil }
            return SleepSample(startDate: cat.startDate, endDate: cat.endDate, stage: stage)
        }
    }

    func fetchTodayStepTotal() async throws -> Int {
        guard HKHealthStore.isHealthDataAvailable() else { return 0 }
        let startOfDay = Calendar.current.startOfDay(for: Date())
        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: Date(), options: .strictStartDate)
        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(
                quantityType: stepType,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum
            ) { _, stats, error in
                if let error { continuation.resume(throwing: error); return }
                let steps = stats?.sumQuantity()?.doubleValue(for: .count()) ?? 0
                continuation.resume(returning: Int(steps.rounded()))
            }
            store.execute(query)
        }
    }
}
```

- [ ] **Step 3: Write `ios/Tests/FakeHealthReader.swift`.**

```swift
import Foundation
@testable import synzoia

final class FakeHealthReader: HealthReading {
    var sleepSamples: [SleepSample] = []
    var stepTotal: Int = 0
    var error: Error?
    private(set) var authorizationRequested = false

    func requestAuthorization() async throws {
        authorizationRequested = true
        if let error { throw error }
    }

    func fetchSleepSamples(from start: Date, to end: Date) async throws -> [SleepSample] {
        if let error { throw error }
        return sleepSamples
    }

    func fetchTodayStepTotal() async throws -> Int {
        if let error { throw error }
        return stepTotal
    }
}
```

- [ ] **Step 4: Regenerate and build (verifies HealthKitReader compiles).**

```bash
cd ios && xcodegen generate && cd ..
xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
```

Expected: `** BUILD SUCCEEDED **`. (If `HKSampleQueryDescriptor` or `HKQuantityType(.stepCount)` raise an availability error, the deployment target is iOS 17 so they are available; report any compile error with the exact text.)

- [ ] **Step 5: Run the full suite (the fake compiles into the test target).**

```bash
xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia \
  -destination 'platform=iOS Simulator,name=iPhone 17' test
```

Expected: `** TEST SUCCEEDED **` (no new tests yet; this confirms the fake and reader build cleanly).

- [ ] **Step 6: Commit.**

```bash
git add ios/Sources/Health/HealthReading.swift ios/Sources/Health/HealthKitReader.swift ios/Tests/FakeHealthReader.swift
git commit -m "feat(ios): HealthReading protocol, HealthKit reader, and test fake"
```

---

### Task 6: SyncEngine

Deliverable: an `@MainActor @Observable SyncEngine` that reads via `HealthReading`, builds payloads, posts via the authed `APIClient`, and exposes observable status. TDD with `FakeHealthReader` + mocked network.

**Files:**
- Create: `ios/Sources/Health/SyncEngine.swift`
- Create: `ios/Tests/SyncEngineTests.swift`

**Interfaces:**
- Consumes: `HealthReading`, `APIClient` (authed), `HealthPayloadBuilder`, `FakeHealthReader`, `MockURLProtocol`.
- Produces:
  - `@MainActor @Observable final class SyncEngine { enum Status: Equatable { case idle; case syncing; case success(Date); case failed(String) }; init(health: HealthReading, api: APIClient, zone: TimeZone = .current, now: @escaping () -> Date = { Date() }); var status: Status { get }; var lastResult: String? { get }; func requestPermission() async; func syncNow() async }`

- [ ] **Step 1: Write the failing tests `ios/Tests/SyncEngineTests.swift`.**

```swift
import XCTest
@testable import synzoia

@MainActor
final class SyncEngineTests: MockedNetworkTestCase {
    private let zone = TimeZone(identifier: "America/Chicago")!
    private let fixedNow = Date(timeIntervalSince1970: 1_781_000_000)

    private func authedClient() -> APIClient {
        APIClient(config: APIConfig(baseURL: URL(string: "https://example.test")!),
                  session: MockURLProtocol.makeSession(), token: "TOK")
    }

    private func sample() -> SleepSample {
        SleepSample(startDate: fixedNow.addingTimeInterval(-3600), endDate: fixedNow, stage: .core)
    }

    func testSuccessfulSyncPostsSleepAndStepsAndReportsSuccess() async {
        var posted: [String] = []
        MockURLProtocol.handler = { request in
            posted.append(request.url!.path)
            let body: Data
            if request.url!.path == "/api/sleep" {
                body = Data(#"{"sessions":[{"id":1,"user_id":1,"session_type":"night","status":"final","review_flag":false,"sleep_date":"2026-06-18","onset":"x","wake":"y","time_in_bed_min":60,"total_asleep_min":60,"awake_min":0,"core_min":60,"deep_min":0,"rem_min":0,"wakeups":0,"efficiency":1.0,"captured_at":"z"}]}"#.utf8)
            } else {
                body = Data(#"{"id":1,"user_id":1,"timestamp":"t","total":8432}"#.utf8)
            }
            return (MockURLProtocol.response(request, status: 201), body)
        }
        let fake = FakeHealthReader()
        fake.sleepSamples = [sample()]
        fake.stepTotal = 8432
        let engine = SyncEngine(health: fake, api: authedClient(), zone: zone, now: { self.fixedNow })

        await engine.syncNow()

        XCTAssertEqual(engine.status, .success(fixedNow))
        XCTAssertTrue(posted.contains("/api/sleep"))
        XCTAssertTrue(posted.contains("/api/steps"))
        XCTAssertEqual(engine.lastResult?.contains("8432"), true)
    }

    func testNoSleepDataStillSyncsStepsAndSucceeds() async {
        var posted: [String] = []
        MockURLProtocol.handler = { request in
            posted.append(request.url!.path)
            return (MockURLProtocol.response(request, status: 201),
                    Data(#"{"id":1,"user_id":1,"timestamp":"t","total":100}"#.utf8))
        }
        let fake = FakeHealthReader()
        fake.sleepSamples = []           // no sleep
        fake.stepTotal = 100
        let engine = SyncEngine(health: fake, api: authedClient(), zone: zone, now: { self.fixedNow })

        await engine.syncNow()

        XCTAssertFalse(posted.contains("/api/sleep"))   // no empty sleep post
        XCTAssertTrue(posted.contains("/api/steps"))
        if case .success = engine.status {} else { XCTFail("expected success") }
    }

    func testSleepPostFailureReportsFailed() async {
        MockURLProtocol.handler = { request in
            if request.url!.path == "/api/sleep" {
                return (MockURLProtocol.response(request, status: 422),
                        Data(#"{"error":{"code":"invalid_payload","message":"Bad payload."}}"#.utf8))
            }
            return (MockURLProtocol.response(request, status: 201), Data(#"{"id":1,"user_id":1,"timestamp":"t","total":1}"#.utf8))
        }
        let fake = FakeHealthReader()
        fake.sleepSamples = [sample()]
        let engine = SyncEngine(health: fake, api: authedClient(), zone: zone, now: { self.fixedNow })

        await engine.syncNow()

        XCTAssertEqual(engine.status, .failed("Bad payload."))
    }

    func testRequestPermissionDelegatesToReader() async {
        let fake = FakeHealthReader()
        let engine = SyncEngine(health: fake, api: authedClient(), zone: zone, now: { self.fixedNow })
        await engine.requestPermission()
        XCTAssertTrue(fake.authorizationRequested)
    }
}
```

- [ ] **Step 2: Run to verify failure.** Expected: "Cannot find 'SyncEngine' in scope".

- [ ] **Step 3: Write `ios/Sources/Health/SyncEngine.swift`.**

```swift
import Foundation
import Observation

/// Reads Apple Health and posts sleep + steps to the backend. Observable so the
/// Settings screen can show progress. Sleep and steps are posted in one pass;
/// an empty sleep window is skipped (an empty body would be a 422).
@MainActor
@Observable
final class SyncEngine {
    enum Status: Equatable {
        case idle
        case syncing
        case success(Date)
        case failed(String)
    }

    private(set) var status: Status = .idle
    private(set) var lastResult: String?

    private let health: HealthReading
    private let api: APIClient
    private let zone: TimeZone
    private let now: () -> Date

    /// Look back this far for sleep, matching the existing Shortcut's window.
    private let sleepLookbackHours: Double = 36

    init(health: HealthReading, api: APIClient, zone: TimeZone = .current, now: @escaping () -> Date = { Date() }) {
        self.health = health
        self.api = api
        self.zone = zone
        self.now = now
    }

    func requestPermission() async {
        try? await health.requestAuthorization()
    }

    func syncNow() async {
        status = .syncing
        let capturedAt = now()
        var parts: [String] = []
        do {
            let start = capturedAt.addingTimeInterval(-sleepLookbackHours * 3600)
            let samples = try await health.fetchSleepSamples(from: start, to: capturedAt)
            if samples.isEmpty {
                parts.append("no new sleep")
            } else {
                let payload = HealthPayloadBuilder.buildSleepPayload(from: samples, capturedAt: capturedAt, zone: zone)
                let sessions = try await api.postSleep(payload)
                parts.append("sleep synced (\(sessions.count) session\(sessions.count == 1 ? "" : "s"))")
            }

            let total = try await health.fetchTodayStepTotal()
            let steps = HealthPayloadBuilder.buildSteps(total: total, capturedAt: capturedAt, zone: zone)
            _ = try await api.postSteps(timestamp: steps.timestamp, total: steps.total)
            parts.append("\(total) steps synced")

            status = .success(capturedAt)
            lastResult = parts.joined(separator: ", ")
        } catch let error as APIError {
            status = .failed(error.userMessage)
            lastResult = "Sync failed: \(error.userMessage)"
        } catch {
            status = .failed("Sync failed. Try again.")
            lastResult = "Sync failed. Try again."
        }
    }
}
```

- [ ] **Step 4: Run tests, verify pass.** Expected: `SyncEngineTests` (4 tests) pass.

- [ ] **Step 5: Commit.**

```bash
git add ios/Sources/Health/SyncEngine.swift ios/Tests/SyncEngineTests.swift
git commit -m "feat(ios): SyncEngine orchestrating health read, build, and post"
```

---

### Task 7: Settings screen, Feed toolbar entry, and auto-sync wiring

Deliverable: a Settings sheet (permission, Sync now, last-sync result, token, sign out) reached from a Feed toolbar button; the signed-in root owns the `SyncEngine` and triggers permission + an initial sync on appear. Views are build-verified.

**Files:**
- Create: `ios/Sources/Features/Settings/SettingsView.swift`
- Create: `ios/Sources/Features/Settings/SignedInView.swift`
- Modify: `ios/Sources/Features/Feed/FeedView.swift` (add an optional settings toolbar button)
- Modify: `ios/Sources/App/RootView.swift` (signed-in branch shows `SignedInView`)

**Interfaces:**
- Consumes: `AppModel`, `SyncEngine`, `HealthKitReader`, `FeedView`.
- Produces: `struct SignedInView: View { init(app: AppModel) }`, `struct SettingsView: View { init(sync: SyncEngine, app: AppModel) }`; `FeedView` gains `init(api: APIClient, onOpenSettings: (() -> Void)? = nil)`.

- [ ] **Step 1: Modify `ios/Sources/Features/Feed/FeedView.swift`** to accept an optional settings action and show a gear toolbar button. Replace the file with:

```swift
import SwiftUI

struct FeedView: View {
    @State private var model: FeedViewModel
    private let onOpenSettings: (() -> Void)?

    init(api: APIClient, onOpenSettings: (() -> Void)? = nil) {
        _model = State(initialValue: FeedViewModel(api: api))
        self.onOpenSettings = onOpenSettings
    }

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Feed")
                .toolbar {
                    if let onOpenSettings {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button {
                                onOpenSettings()
                            } label: {
                                Image(systemName: "gearshape")
                            }
                            .accessibilityLabel("Settings")
                        }
                    }
                }
        }
        .task { await model.load() }
    }

    @ViewBuilder
    private var content: some View {
        switch model.state {
        case .loading:
            ProgressView("Loading feed...")
        case .empty:
            ContentUnavailableView("No posts yet", systemImage: "moon.zzz",
                                   description: Text("Posts from your crew will show up here."))
        case .failed(let message):
            VStack(spacing: 12) {
                Text(message).foregroundStyle(.secondary)
                Button("Try again") { Task { await model.load() } }
                    .buttonStyle(.bordered)
            }
        case .loaded(let posts):
            List(posts) { post in
                PostRow(post: post)
            }
            .listStyle(.plain)
            .refreshable { await model.refresh() }
        }
    }
}

#Preview {
    FeedView(api: APIClient(config: .production))
}
```

- [ ] **Step 2: Write `ios/Sources/Features/Settings/SettingsView.swift`.**

```swift
import SwiftUI

struct SettingsView: View {
    let sync: SyncEngine
    let app: AppModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section("Apple Health") {
                    Button("Allow Apple Health access") {
                        Task { await sync.requestPermission() }
                    }
                    Button {
                        Task { await sync.syncNow() }
                    } label: {
                        if case .syncing = sync.status {
                            HStack { ProgressView(); Text("Syncing...") }
                        } else {
                            Text("Sync now")
                        }
                    }
                    .disabled(sync.status == .syncing)

                    if let lastResult = sync.lastResult {
                        Text(lastResult).font(.footnote).foregroundStyle(.secondary)
                    }
                    if case .failed(let message) = sync.status {
                        Text(message).font(.footnote).foregroundStyle(.red)
                    }
                }

                Section("Your token") {
                    Text(app.token ?? "Not signed in")
                        .font(.system(.footnote, design: .monospaced))
                        .textSelection(.enabled)
                    Text("Save this. It is the only way back into your account.")
                        .font(.caption).foregroundStyle(.secondary)
                }

                Section {
                    Button("Sign out", role: .destructive) {
                        app.signOut()
                        dismiss()
                    }
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
```

- [ ] **Step 3: Write `ios/Sources/Features/Settings/SignedInView.swift`.**

```swift
import SwiftUI

/// Shown when the user has a token. Owns the SyncEngine (built with the
/// authenticated client) and hosts the Feed plus the Settings sheet. Requests
/// Health permission and runs an initial sync when it first appears.
struct SignedInView: View {
    let app: AppModel
    @State private var sync: SyncEngine
    @State private var showSettings = false

    init(app: AppModel) {
        self.app = app
        _sync = State(initialValue: SyncEngine(health: HealthKitReader(), api: app.authedClient()))
    }

    var body: some View {
        FeedView(api: app.api, onOpenSettings: { showSettings = true })
            .sheet(isPresented: $showSettings) {
                SettingsView(sync: sync, app: app)
            }
            .task {
                await sync.requestPermission()
                await sync.syncNow()
            }
    }
}
```

- [ ] **Step 4: Modify `ios/Sources/App/RootView.swift`** so the signed-in branch shows `SignedInView`.

```swift
import SwiftUI

struct RootView: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        if app.isSignedIn {
            SignedInView(app: app)
        } else {
            OnboardingView(api: app.api, onSignIn: { token in
                app.signIn(token: token)
            })
        }
    }
}
```

- [ ] **Step 5: Regenerate and build.**

```bash
cd ios && xcodegen generate && cd ..
xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
```

Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 6: Run the full suite.**

```bash
xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia \
  -destination 'platform=iOS Simulator,name=iPhone 17' test
```

Expected: `** TEST SUCCEEDED **` (all suites: the Phase 0+1 tests plus SleepStageMapping, HealthPayloadBuilder, HealthEndpoints, SyncEngine).

- [ ] **Step 7: Commit.**

```bash
git add ios/Sources/Features/Settings ios/Sources/Features/Feed/FeedView.swift ios/Sources/App/RootView.swift
git commit -m "feat(ios): Settings sheet with Sync now and auto-sync on launch"
```

---

### Task 8: Device validation (human) and final verification

Deliverable: the app is confirmed reading real Apple Health data and posting it on a physical iPhone, plus a final clean simulator suite. The agent does the simulator verification and the screenshot; the human does the device-only steps.

**Files:** none (verification + documentation).

- [ ] **Step 1 (agent): Final full-suite run + Settings screenshot.**

```bash
xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia \
  -destination 'platform=iOS Simulator,name=iPhone 17' test
APP=$(find ~/Library/Developer/Xcode/DerivedData/synzoia-*/Build/Products/Debug-iphonesimulator -name "synzoia.app" | head -1)
xcrun simctl install "iPhone 17" "$APP" 2>/dev/null || true
xcrun simctl launch "iPhone 17" com.synzoia.ios
```

Expected: `** TEST SUCCEEDED **`. (The simulator has no real Health data, so the Sync-now button will report "no new sleep" plus a step count of 0 there; that is expected. Real data is the device step below.)

- [ ] **Step 2 (human, in Xcode, one time): Signing + HealthKit capability.**
  - Open `ios/synzoia.xcodeproj`.
  - Select the `synzoia` target > Signing & Capabilities > pick your personal team (your Apple ID). This fills `DEVELOPMENT_TEAM`.
  - Click "+ Capability" and add **HealthKit** (a free Apple ID is allowed to add HealthKit). Xcode mints a provisioning profile including the entitlement.

- [ ] **Step 3 (human): Run on your iPhone.**
  - Connect the iPhone via USB, select it as the run destination, and click Run (Cmd+R).
  - Trust the computer on the phone if prompted; after install, trust the developer at Settings > General > VPN & Device Management.
  - On launch the app asks for Apple Health access: grant Sleep and Steps.

- [ ] **Step 4 (human): Verify real sync.**
  - Open Settings (gear icon on the Feed), tap "Sync now". It should report your real step count and, if you have a recent night, "sleep synced".
  - Confirm the post appears: pull to refresh the Feed, or check `https://synzoia.vercel.app` in a browser for your sleep/steps posts.
  - If "Sync now" reports "no new sleep" but you have sleep data, check that you granted Sleep access in the Apple Health app (Settings > Health > Data Access & Devices > synzoia). Remember a denied read looks identical to no data.

- [ ] **Step 5 (human): Note the 7-day expiry.** With a free Apple ID the build stops launching after 7 days; re-run from Xcode to refresh. Move to the paid program at Phase 5 (TestFlight).

- [ ] **Step 6 (agent): Record outcome.** Once the human confirms a real sleep or steps post landed, the phase is complete. No commit (verification only).

---

## Self-Review

**1. Spec coverage (Phase 2 scope):**
- Spec Phase 2 "HealthKit permission" -> Tasks 1, 5 (entitlement + `requestAuthorization`). "read sleep" -> Task 5 (`HealthKitReader.fetchSleepSamples`). "SyncEngine + POST /api/sleep" -> Tasks 4, 6. "manual Sync now" -> Task 7. "First real-device run" -> Task 8. Steps sync (added to Phase 2 scope) -> Tasks 3, 4, 5, 6. All covered.
- Verified contract honored: stages in `values` (Task 2 mapping + Task 3 builder), `types` = "Sleep" (Task 3), `duration` from real dates in bare seconds (Task 3 + the explicit test), offset-bearing `timestamp` (Task 3), steps MAX-per-day idempotency relied on (Task 6 re-post safety), read-auth opacity surfaced as "no new sleep" not "denied" (Tasks 6, 7, 8 checklist).
- Apple-frameworks-only: only `HealthKitReader.swift` imports HealthKit; everything else is Foundation/SwiftUI/Observation. No SPM.

**2. Placeholder scan:** No "TBD"/"TODO". Every code step has complete code; every test step has complete tests; entitlement/Info.plist/project.yml snippets are concrete. Task 8's human steps are genuine external actions (signing, device), not placeholders, and are explicitly delegated.

**3. Type consistency:** `SleepSample`/`Stage`, `mapSleepStage(hkRawValue:)`, `SleepPayload`, `HealthPayloadBuilder.buildSleepPayload(from:capturedAt:zone:)`/`buildSteps(total:capturedAt:zone:)`, `SleepSession`/`IngestSleepResponse`/`CreateStepRequest`/`CreateStepResponse`, `APIClient.postSleep(_:)`/`postSteps(timestamp:total:)`, `HealthReading`/`HealthKitReader`/`FakeHealthReader`, `SyncEngine(health:api:zone:now:)`/`Status`/`syncNow()`/`requestPermission()`, `SignedInView(app:)`, `SettingsView(sync:app:)`, `FeedView(api:onOpenSettings:)` are used identically across defining and consuming tasks. Test classes that use the network mock subclass `MockedNetworkTestCase` (from the Phase 0+1 fix) so the handler resets between tests.
