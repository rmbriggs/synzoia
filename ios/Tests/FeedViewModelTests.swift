import XCTest
@testable import synzoia

@MainActor
final class FeedViewModelTests: MockedNetworkTestCase {
    private func api() -> APIClient {
        APIClient(config: APIConfig(baseURL: URL(string: "https://example.test")!),
                  session: MockURLProtocol.makeSession())
    }

    func testLoadPopulatesPosts() async {
        MockURLProtocol.handler = { request in
            let body = Data(#"{"posts":[{"id":1,"user_id":2,"username":"a","type":"steps","timestamp":"t","details":null,"body":null}]}"#.utf8)
            return (MockURLProtocol.response(request, status: 200), body)
        }
        let vm = FeedViewModel(api: api())
        await vm.load()
        guard case .loaded(let posts) = vm.state else { return XCTFail("expected loaded") }
        XCTAssertEqual(posts.count, 1)
    }

    func testEmptyFeedYieldsEmptyState() async {
        MockURLProtocol.handler = { request in
            (MockURLProtocol.response(request, status: 200), Data(#"{"posts":[]}"#.utf8))
        }
        let vm = FeedViewModel(api: api())
        await vm.load()
        XCTAssertEqual(vm.state, .empty)
    }

    func testServerErrorYieldsFailedState() async {
        MockURLProtocol.handler = { request in
            let body = Data(#"{"error":{"code":"server_error","message":"Boom."}}"#.utf8)
            return (MockURLProtocol.response(request, status: 500), body)
        }
        let vm = FeedViewModel(api: api())
        await vm.load()
        XCTAssertEqual(vm.state, .failed("Boom."))
    }
}
