import XCTest
@testable import synzoia

@MainActor
final class AppModelTests: XCTestCase {
    func testStartsSignedOutWhenNoToken() {
        let model = AppModel(store: InMemoryTokenStore(nil))
        XCTAssertFalse(model.isSignedIn)
    }

    func testStartsSignedInWhenTokenPresent() {
        let model = AppModel(store: InMemoryTokenStore("EXISTING"))
        XCTAssertTrue(model.isSignedIn)
    }

    func testSignInPersistsAndFlips() {
        let store = InMemoryTokenStore(nil)
        let model = AppModel(store: store)
        model.signIn(token: "NEW", username: "tester")
        XCTAssertTrue(model.isSignedIn)
        XCTAssertEqual(store.load(), "NEW")
    }

    func testSignOutClears() {
        let store = InMemoryTokenStore("X")
        let model = AppModel(store: store)
        model.signOut()
        XCTAssertFalse(model.isSignedIn)
        XCTAssertNil(store.load())
    }
}
