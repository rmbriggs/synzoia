import XCTest
@testable import synzoia

final class GradientAvatarTests: XCTestCase {
    func testInitialsTakeFirstTwoLettersUppercased() {
        XCTAssertEqual(AvatarStyle.initials("micah"), "MI")
        XCTAssertEqual(AvatarStyle.initials("a"), "A")
        XCTAssertEqual(AvatarStyle.initials("@angela"), "AN")   // strips a leading @
        XCTAssertEqual(AvatarStyle.initials(""), "?")
    }

    func testGradientIsDeterministicAndTwoStops() {
        let g1 = AvatarStyle.gradient("micah")
        let g2 = AvatarStyle.gradient("micah")
        XCTAssertEqual(g1.count, 2)
        XCTAssertEqual(g1, g2)                                  // same username -> same gradient
        // different usernames generally differ; at least the API is stable
        XCTAssertEqual(AvatarStyle.gradient("angela").count, 2)
    }
}
