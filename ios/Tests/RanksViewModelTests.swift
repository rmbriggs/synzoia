import XCTest
@testable import synzoia

// MARK: - Fixtures

private let stepsRankingJSON = Data(#"""
{
    "week_start": "2026-06-15",
    "week_end":   "2026-06-21",
    "leaderboard": [
        {"rank": 1, "username": "angela", "total": 550000},
        {"rank": 2, "username": "micah",  "total": 412800},
        {"rank": 3, "username": "peter",  "total": 300000}
    ],
    "daily_breakdown": [{"date": "2026-06-15", "total": 8500}]
}
"""#.utf8)

private let sleepRankingJSON = Data(#"""
{
    "week_start": "2026-06-15",
    "week_end":   "2026-06-21",
    "leaderboard": [
        {"rank": 1, "username": "micah",  "total": 480},
        {"rank": 2, "username": "angela", "total": 420}
    ],
    "daily_breakdown": [{"date": "2026-06-15", "total": 480}]
}
"""#.utf8)

private let errorJSON = Data(#"{"error":{"code":"server_error","message":"Something went wrong."}}"#.utf8)

// MARK: - Tests

@MainActor
final class RanksViewModelTests: MockedNetworkTestCase {

    private func api() -> APIClient {
        APIClient(
            config: APIConfig(baseURL: URL(string: "https://example.test")!),
            session: MockURLProtocol.makeSession()
        )
    }

    // MARK: Successful load

    func testLoadTransitionsToLoaded() async {
        MockURLProtocol.handler = { req in
            let body = req.url?.path.contains("sleep") == true ? sleepRankingJSON : stepsRankingJSON
            return (MockURLProtocol.response(req, status: 200), body)
        }
        let vm = RanksViewModel(api: api(), currentUsername: "micah")
        await vm.load()
        XCTAssertEqual(vm.state, .loaded)
    }

    func testLoadPopulatesBothRankings() async {
        MockURLProtocol.handler = { req in
            let body = req.url?.path.contains("sleep") == true ? sleepRankingJSON : stepsRankingJSON
            return (MockURLProtocol.response(req, status: 200), body)
        }
        let vm = RanksViewModel(api: api(), currentUsername: "micah")
        await vm.load()
        XCTAssertNotNil(vm.stepsRanking, "stepsRanking should be populated after load")
        XCTAssertNotNil(vm.sleepRanking, "sleepRanking should be populated after load")
    }

    func testLeaderStepsIsRankOne() async {
        MockURLProtocol.handler = { req in
            let body = req.url?.path.contains("sleep") == true ? sleepRankingJSON : stepsRankingJSON
            return (MockURLProtocol.response(req, status: 200), body)
        }
        let vm = RanksViewModel(api: api(), currentUsername: "micah")
        await vm.load()
        XCTAssertEqual(vm.leader(.steps), RankEntry(rank: 1, username: "angela", total: 550000))
    }

    func testLeaderSleepIsRankOne() async {
        MockURLProtocol.handler = { req in
            let body = req.url?.path.contains("sleep") == true ? sleepRankingJSON : stepsRankingJSON
            return (MockURLProtocol.response(req, status: 200), body)
        }
        let vm = RanksViewModel(api: api(), currentUsername: "micah")
        await vm.load()
        XCTAssertEqual(vm.leader(.sleep), RankEntry(rank: 1, username: "micah", total: 480))
    }

    func testMyEntryFindsCurrentUser() async {
        MockURLProtocol.handler = { req in
            let body = req.url?.path.contains("sleep") == true ? sleepRankingJSON : stepsRankingJSON
            return (MockURLProtocol.response(req, status: 200), body)
        }
        let vm = RanksViewModel(api: api(), currentUsername: "micah")
        await vm.load()
        // micah is rank 2 in steps
        XCTAssertEqual(vm.myEntry(.steps), RankEntry(rank: 2, username: "micah", total: 412800))
    }

    func testMyEntryNilWhenUserNotInLeaderboard() async {
        MockURLProtocol.handler = { req in
            let body = req.url?.path.contains("sleep") == true ? sleepRankingJSON : stepsRankingJSON
            return (MockURLProtocol.response(req, status: 200), body)
        }
        let vm = RanksViewModel(api: api(), currentUsername: "ghost")
        await vm.load()
        XCTAssertNil(vm.myEntry(.steps))
        XCTAssertNil(vm.myEntry(.sleep))
    }

    func testMyEntryNilWhenCurrentUsernameIsNil() async {
        MockURLProtocol.handler = { req in
            let body = req.url?.path.contains("sleep") == true ? sleepRankingJSON : stepsRankingJSON
            return (MockURLProtocol.response(req, status: 200), body)
        }
        let vm = RanksViewModel(api: api(), currentUsername: nil)
        await vm.load()
        XCTAssertNil(vm.myEntry(.steps))
    }

    // MARK: Error handling

    func testServerErrorYieldsFailedState() async {
        MockURLProtocol.handler = { req in
            (MockURLProtocol.response(req, status: 500), errorJSON)
        }
        let vm = RanksViewModel(api: api(), currentUsername: "micah")
        await vm.load()
        if case .failed(let msg) = vm.state {
            XCTAssertFalse(msg.isEmpty)
        } else {
            XCTFail("Expected .failed, got \(vm.state)")
        }
    }

    func testLeaderReturnsNilBeforeLoad() {
        let vm = RanksViewModel(api: api(), currentUsername: "micah")
        XCTAssertNil(vm.leader(.steps))
        XCTAssertNil(vm.leader(.sleep))
    }

    func testInitialStateIsLoading() {
        let vm = RanksViewModel(api: api(), currentUsername: "micah")
        XCTAssertEqual(vm.state, .loading)
    }
}
