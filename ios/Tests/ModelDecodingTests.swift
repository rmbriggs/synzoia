import XCTest
@testable import synzoia

final class ModelDecodingTests: XCTestCase {
    private let decoder = APIClient.decoder

    func testCreateProfileResponseDecodes() throws {
        let json = Data(#"{"username":"alice","token":"AHDE-VHSE-CNCX-HELJ","join_date":"2026-06-18T14:30:00"}"#.utf8)
        let r = try decoder.decode(CreateProfileResponse.self, from: json)
        XCTAssertEqual(r, CreateProfileResponse(username: "alice", token: "AHDE-VHSE-CNCX-HELJ", joinDate: "2026-06-18T14:30:00"))
    }

    func testFeedDecodesSleepAndStepsPosts() throws {
        let json = Data(#"""
        {"posts":[
          {"id":456,"user_id":45,"username":"alice","type":"sleep","timestamp":"2026-06-18T06:35:00","details":{"night_of":"2026-06-17","duration_min":462},"body":null},
          {"id":457,"user_id":45,"username":"alice","type":"steps","timestamp":"2026-06-18T10:30:00","details":null,"body":null}
        ]}
        """#.utf8)
        let r = try decoder.decode(FeedResponse.self, from: json)
        XCTAssertEqual(r.posts.count, 2)
        XCTAssertEqual(r.posts[0].type, "sleep")
        XCTAssertEqual(r.posts[0].details?.nightOf, "2026-06-17")
        XCTAssertEqual(r.posts[0].details?.durationMin, 462)
        XCTAssertNil(r.posts[1].details)
    }

    func testFeedDecodesRecapPost() throws {
        let json = Data(#"""
        {"posts":[
          {"id":99,"user_id":1,"username":"system","type":"leaderboard_recap","timestamp":"2026-06-18T11:00:00",
           "details":{"date":"2026-06-17","top":[{"username":"bob","total":175000}]},"body":null}
        ]}
        """#.utf8)
        let r = try decoder.decode(FeedResponse.self, from: json)
        XCTAssertEqual(r.posts[0].details?.top?.first, RecapEntry(username: "bob", total: 175000))
    }
}
