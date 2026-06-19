import XCTest

/// Base class for test cases that use MockURLProtocol.
/// Resets the handler after each test to prevent state leaking between tests.
class MockedNetworkTestCase: XCTestCase {
    override func tearDown() {
        MockURLProtocol.handler = nil
        super.tearDown()
    }
}
