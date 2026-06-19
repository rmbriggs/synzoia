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
        } catch {
            XCTFail("unexpected error type: \(error)")
        }
    }
}
