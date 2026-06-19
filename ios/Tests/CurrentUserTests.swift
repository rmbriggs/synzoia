import XCTest
@testable import synzoia

final class CurrentUserStoreTests: XCTestCase {
    func testInMemoryStoresUsername() {
        let s = InMemoryTokenStore(nil)
        XCTAssertNil(s.loadUsername())
        s.saveUsername("micah")
        XCTAssertEqual(s.loadUsername(), "micah")
        s.clear()
        XCTAssertNil(s.loadUsername())
    }

    func testKeychainStoresUsername() {
        let store = KeychainTokenStore()
        store.clear()
        XCTAssertNil(store.loadUsername())
        store.saveUsername("alice")
        XCTAssertEqual(store.loadUsername(), "alice")
        store.saveUsername("bob")
        XCTAssertEqual(store.loadUsername(), "bob")
        store.clear()
        XCTAssertNil(store.loadUsername())
    }
}

@MainActor
final class AppModelUsernameTests: XCTestCase {
    func testSignInPersistsUsername() {
        let store = InMemoryTokenStore(nil)
        let model = AppModel(store: store)
        model.signIn(token: "TOK", username: "micah")
        XCTAssertEqual(model.username, "micah")
        XCTAssertEqual(store.loadUsername(), "micah")
    }
    func testStartsWithStoredUsername() {
        let store = InMemoryTokenStore("TOK"); store.saveUsername("angela")
        let model = AppModel(store: store)
        XCTAssertEqual(model.username, "angela")
    }
    func testSignOutClearsUsername() {
        let store = InMemoryTokenStore("TOK"); store.saveUsername("x")
        let model = AppModel(store: store)
        model.signOut()
        XCTAssertNil(model.username)
        XCTAssertNil(store.loadUsername())
    }
}
