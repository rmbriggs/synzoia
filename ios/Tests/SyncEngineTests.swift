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
