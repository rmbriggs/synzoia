import XCTest
@testable import synzoia

final class EndpointsTests: XCTestCase {
    private func client() -> APIClient {
        APIClient(config: APIConfig(baseURL: URL(string: "https://example.test")!),
                  session: MockURLProtocol.makeSession())
    }

    func testCreateProfileHitsProfilesAndReturnsToken() async throws {
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/profiles")
            XCTAssertEqual(request.httpMethod, "POST")
            let body = Data(#"{"username":"alice","token":"TOK","join_date":"2026-06-18T00:00:00"}"#.utf8)
            return (MockURLProtocol.response(request, status: 201), body)
        }
        let r = try await client().createProfile(username: "alice")
        XCTAssertEqual(r.token, "TOK")
    }

    func testFetchFeedReturnsPostsArray() async throws {
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/posts")
            let body = Data(#"{"posts":[{"id":1,"user_id":2,"username":"a","type":"steps","timestamp":"t","details":null,"body":null}]}"#.utf8)
            return (MockURLProtocol.response(request, status: 200), body)
        }
        let posts = try await client().fetchFeed(limit: 50)
        XCTAssertEqual(posts.count, 1)
        XCTAssertEqual(posts.first?.id, 1)
    }
}
