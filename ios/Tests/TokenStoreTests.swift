import XCTest
@testable import synzoia

final class TokenStoreTests: XCTestCase {
    func testInMemoryRoundTrip() {
        let store = InMemoryTokenStore(nil)
        XCTAssertNil(store.load())
        store.save("TOK-1")
        XCTAssertEqual(store.load(), "TOK-1")
        store.clear()
        XCTAssertNil(store.load())
    }

    func testKeychainRoundTrip() {
        let store = KeychainTokenStore()
        store.clear()
        XCTAssertNil(store.load())
        store.save("KC-TOKEN")
        XCTAssertEqual(store.load(), "KC-TOKEN")
        store.save("KC-TOKEN-2")            // overwrite path
        XCTAssertEqual(store.load(), "KC-TOKEN-2")
        store.clear()
        XCTAssertNil(store.load())
    }
}
