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
