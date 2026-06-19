import XCTest
@testable import synzoia

final class APIClientTests: MockedNetworkTestCase {
    private func makeClient(token: String? = nil) -> APIClient {
        APIClient(config: APIConfig(baseURL: URL(string: "https://example.test")!),
                  session: MockURLProtocol.makeSession(),
                  token: token)
    }

    private struct Echo: Decodable, Equatable { let ok: Bool }

    func testGetBuildsCorrectURLAndDecodes() async throws {
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.absoluteString, "https://example.test/api/health")
            XCTAssertEqual(request.httpMethod, "GET")
            return (MockURLProtocol.response(request, status: 200), Data(#"{"ok":true}"#.utf8))
        }
        let result: Echo = try await makeClient().get("/api/health", query: [])
        XCTAssertEqual(result, Echo(ok: true))
    }

    func testGetAppendsQueryItems() async throws {
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.query, "limit=5")
            return (MockURLProtocol.response(request, status: 200), Data(#"{"ok":true}"#.utf8))
        }
        let _: Echo = try await makeClient().get("/api/posts", query: [URLQueryItem(name: "limit", value: "5")])
    }

    func testPostAttachesBearerTokenAndJSONBody() async throws {
        struct Body: Encodable { let username: String }
        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer TOK-123")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
            return (MockURLProtocol.response(request, status: 201), Data(#"{"ok":true}"#.utf8))
        }
        let _: Echo = try await makeClient(token: "TOK-123").post("/api/profiles", body: Body(username: "a"))
    }

    func testNon2xxMapsToHTTPError() async throws {
        MockURLProtocol.handler = { request in
            let body = Data(#"{"error":{"code":"username_taken","message":"That name is taken."}}"#.utf8)
            return (MockURLProtocol.response(request, status: 409), body)
        }
        do {
            let _: Echo = try await makeClient().get("/api/x", query: [])
            XCTFail("expected error")
        } catch let error as APIError {
            XCTAssertEqual(error, .http(status: 409, code: "username_taken", message: "That name is taken."))
        }
    }
}
