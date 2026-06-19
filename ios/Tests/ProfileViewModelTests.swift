import XCTest
@testable import synzoia

// MARK: - Fixtures

private let stepsSummaryJSON = Data(#"""
{
    "username": "micah",
    "join_date": "2026-01-15",
    "score": 412800,
    "rank": 2,
    "best_day": {"date": "2026-06-01", "total": 24500}
}
"""#.utf8)

private let stepsSummaryNilScoreJSON = Data(#"""
{
    "username": "ghost"
}
"""#.utf8)

private let stepsWeeklyJSON = Data(#"""
{
    "username": "micah",
    "weekly_total": 82000,
    "rank_this_week": 1,
    "daily_breakdown": [
        {"date": "2026-06-13", "total": 10000},
        {"date": "2026-06-14", "total": 12500},
        {"date": "2026-06-15", "total": 9800},
        {"date": "2026-06-16", "total": 14200},
        {"date": "2026-06-17", "total": 11300},
        {"date": "2026-06-18", "total": 13100},
        {"date": "2026-06-19", "total": 11100}
    ]
}
"""#.utf8)

private let stepsWeeklyEmptyJSON = Data(#"""
{
    "username": "ghost",
    "weekly_total": null,
    "rank_this_week": null,
    "daily_breakdown": []
}
"""#.utf8)

private let profilesJSON = Data(#"""
{
    "profiles": [
        {"username": "micah", "join_date": "2026-01-15", "total_steps_all_time": 1234567},
        {"username": "angela", "join_date": "2026-02-01", "total_steps_all_time": 987000}
    ]
}
"""#.utf8)

private let profilesEmptyJSON = Data(#"""
{"profiles": []}
"""#.utf8)

private let errorJSON = Data(#"{"error":{"code":"server_error","message":"Something went wrong."}}"#.utf8)

// MARK: - Tests

@MainActor
final class ProfileViewModelTests: MockedNetworkTestCase {

    private func api() -> APIClient {
        APIClient(
            config: APIConfig(baseURL: URL(string: "https://example.test")!),
            session: MockURLProtocol.makeSession()
        )
    }

    private func handler(
        summaryData: Data,
        weeklyData: Data,
        profilesData: Data = profilesJSON
    ) -> (URLRequest) throws -> (HTTPURLResponse, Data) {
        { req in
            let path = req.url?.path ?? ""
            let body: Data
            if path == "/api/profiles" {
                body = profilesData
            } else if path.contains("/weekly") {
                body = weeklyData
            } else {
                body = summaryData
            }
            return (MockURLProtocol.response(req, status: 200), body)
        }
    }

    // MARK: Initial state

    func testInitialStateIsLoading() {
        let vm = ProfileViewModel(api: api(), username: "micah")
        XCTAssertEqual(vm.state, .loading)
        XCTAssertNil(vm.stepsSummary)
        XCTAssertNil(vm.stepsWeekly)
        XCTAssertNil(vm.profileSummary)
    }

    // MARK: Successful load

    func testLoadTransitionsToLoaded() async {
        MockURLProtocol.handler = handler(summaryData: stepsSummaryJSON, weeklyData: stepsWeeklyJSON)
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        XCTAssertEqual(vm.state, .loaded)
    }

    func testLoadPopulatesSummary() async {
        MockURLProtocol.handler = handler(summaryData: stepsSummaryJSON, weeklyData: stepsWeeklyJSON)
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        XCTAssertNotNil(vm.stepsSummary, "stepsSummary should be populated after load")
        XCTAssertEqual(vm.stepsSummary?.username, "micah")
        XCTAssertEqual(vm.stepsSummary?.score, 412800)
        XCTAssertEqual(vm.stepsSummary?.rank, 2)
    }

    func testLoadPopulatesWeekly() async {
        MockURLProtocol.handler = handler(summaryData: stepsSummaryJSON, weeklyData: stepsWeeklyJSON)
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        XCTAssertNotNil(vm.stepsWeekly, "stepsWeekly should be populated after load")
        XCTAssertEqual(vm.stepsWeekly?.dailyBreakdown.count, 7)
        XCTAssertEqual(vm.stepsWeekly?.weeklyTotal, 82000)
    }

    func testLoadPopulatesSummaryJoinDate() async {
        MockURLProtocol.handler = handler(summaryData: stepsSummaryJSON, weeklyData: stepsWeeklyJSON)
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        XCTAssertEqual(vm.stepsSummary?.joinDate, "2026-01-15")
    }

    // MARK: All-time steps from profiles API

    func testLoadPopulatesProfileSummaryAllTimeSteps() async {
        MockURLProtocol.handler = handler(summaryData: stepsSummaryJSON, weeklyData: stepsWeeklyJSON)
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        XCTAssertNotNil(vm.profileSummary, "profileSummary should be populated for known user")
        XCTAssertEqual(vm.profileSummary?.totalStepsAllTime, 1234567,
                       "all-time steps should come from /api/profiles, not the 30-day score")
        XCTAssertEqual(vm.profileSummary?.joinDate, "2026-01-15")
    }

    func testProfileSummaryNilWhenUserNotInProfilesList() async {
        MockURLProtocol.handler = handler(
            summaryData: stepsSummaryNilScoreJSON,
            weeklyData: stepsWeeklyEmptyJSON,
            profilesData: profilesEmptyJSON
        )
        let vm = ProfileViewModel(api: api(), username: "ghost")
        await vm.load()
        XCTAssertEqual(vm.state, .loaded)
        XCTAssertNil(vm.profileSummary, "profileSummary nil when user absent from profiles list")
    }

    func testAllTimeStepsDifferentFrom30DayScore() async {
        // 30-day score = 412800 but all-time = 1234567: they must not be conflated.
        MockURLProtocol.handler = handler(summaryData: stepsSummaryJSON, weeklyData: stepsWeeklyJSON)
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        XCTAssertNotEqual(vm.profileSummary?.totalStepsAllTime, vm.stepsSummary?.score,
                          "all-time steps and 30-day score should be distinct values")
    }

    // MARK: Nil score / rank handled gracefully

    func testNilScoreAndRankDoNotCrash() async {
        MockURLProtocol.handler = handler(summaryData: stepsSummaryNilScoreJSON, weeklyData: stepsWeeklyEmptyJSON)
        let vm = ProfileViewModel(api: api(), username: "ghost")
        await vm.load()
        XCTAssertEqual(vm.state, .loaded)
        XCTAssertNil(vm.stepsSummary?.score)
        XCTAssertNil(vm.stepsSummary?.rank)
    }

    func testNilWeeklyTotalDoesNotCrash() async {
        MockURLProtocol.handler = handler(summaryData: stepsSummaryNilScoreJSON, weeklyData: stepsWeeklyEmptyJSON)
        let vm = ProfileViewModel(api: api(), username: "ghost")
        await vm.load()
        XCTAssertEqual(vm.state, .loaded)
        XCTAssertNil(vm.stepsWeekly?.weeklyTotal)
        XCTAssertEqual(vm.stepsWeekly?.dailyBreakdown.count, 0)
    }

    // MARK: Error handling

    func testServerErrorYieldsFailedState() async {
        MockURLProtocol.handler = { req in
            (MockURLProtocol.response(req, status: 500), errorJSON)
        }
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        if case .failed(let msg) = vm.state {
            XCTAssertFalse(msg.isEmpty)
        } else {
            XCTFail("Expected .failed, got \(vm.state)")
        }
    }

    func testFailedStateClearsData() async {
        MockURLProtocol.handler = { req in
            (MockURLProtocol.response(req, status: 500), errorJSON)
        }
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        XCTAssertNil(vm.stepsSummary)
        XCTAssertNil(vm.stepsWeekly)
        XCTAssertNil(vm.profileSummary)
    }

    // MARK: Load uses correct username in path

    func testLoadRequestsCorrectUsername() async {
        var capturedPaths: [String] = []
        MockURLProtocol.handler = { req in
            capturedPaths.append(req.url?.path ?? "")
            let path = req.url?.path ?? ""
            if path == "/api/profiles" { return (MockURLProtocol.response(req, status: 200), profilesJSON) }
            return (MockURLProtocol.response(req, status: 200), path.contains("/weekly") ? stepsWeeklyJSON : stepsSummaryJSON)
        }
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        XCTAssertTrue(capturedPaths.contains { $0.contains("micah") && $0.contains("summary") },
                      "should request summary for micah, got: \(capturedPaths)")
        XCTAssertTrue(capturedPaths.contains { $0.contains("micah") && $0.contains("weekly") },
                      "should request weekly for micah, got: \(capturedPaths)")
        XCTAssertTrue(capturedPaths.contains { $0 == "/api/profiles" },
                      "should request /api/profiles, got: \(capturedPaths)")
    }

    // MARK: Retry resets to loading then resolves

    func testRetryFromFailedStateReloads() async {
        var callCount = 0
        MockURLProtocol.handler = { req in
            callCount += 1
            if callCount <= 3 {
                return (MockURLProtocol.response(req, status: 500), errorJSON)
            }
            let path = req.url?.path ?? ""
            if path == "/api/profiles" { return (MockURLProtocol.response(req, status: 200), profilesJSON) }
            return (MockURLProtocol.response(req, status: 200), path.contains("/weekly") ? stepsWeeklyJSON : stepsSummaryJSON)
        }
        let vm = ProfileViewModel(api: api(), username: "micah")
        await vm.load()
        XCTAssertEqual(vm.state, .failed("Something went wrong."))

        // Second call succeeds
        await vm.load()
        XCTAssertEqual(vm.state, .loaded)
        XCTAssertNotNil(vm.stepsSummary)
    }
}
