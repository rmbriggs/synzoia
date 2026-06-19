import XCTest
@testable import synzoia

@MainActor
final class OnboardingViewModelTests: MockedNetworkTestCase {
    private func api() -> APIClient {
        APIClient(config: APIConfig(baseURL: URL(string: "https://example.test")!),
                  session: MockURLProtocol.makeSession())
    }

    func testSuccessfulJoinCallsOnSignInWithToken() async {
        MockURLProtocol.handler = { request in
            let body = Data(#"{"username":"alice","token":"TOK-9","join_date":"2026-06-18T00:00:00"}"#.utf8)
            return (MockURLProtocol.response(request, status: 201), body)
        }
        var signedInWith: String?
        let vm = OnboardingViewModel(api: api(), onSignIn: { signedInWith = $0 })
        vm.username = "  alice  "      // trims whitespace
        await vm.join()
        XCTAssertEqual(signedInWith, "TOK-9")
        XCTAssertEqual(vm.mintedToken, "TOK-9")
        XCTAssertEqual(vm.state, .idle)
    }

    func testTakenUsernameSurfacesError() async {
        MockURLProtocol.handler = { request in
            let body = Data(#"{"error":{"code":"username_taken","message":"That name is taken."}}"#.utf8)
            return (MockURLProtocol.response(request, status: 409), body)
        }
        var called = false
        let vm = OnboardingViewModel(api: api(), onSignIn: { _ in called = true })
        vm.username = "alice"
        await vm.join()
        XCTAssertEqual(vm.state, .failed("That name is taken."))
        XCTAssertFalse(called)
    }

    func testCanSubmitRequiresNonEmptyUsername() {
        let vm = OnboardingViewModel(api: api(), onSignIn: { _ in })
        XCTAssertFalse(vm.canSubmit)
        vm.username = "x"
        XCTAssertTrue(vm.canSubmit)
    }
}
