import Foundation
@testable import synzoia

final class FakeHealthReader: HealthReading {
    var sleepSamples: [SleepSample] = []
    var stepTotal: Int = 0
    var error: Error?
    private(set) var authorizationRequested = false

    func requestAuthorization() async throws {
        authorizationRequested = true
        if let error { throw error }
    }

    func fetchSleepSamples(from start: Date, to end: Date) async throws -> [SleepSample] {
        if let error { throw error }
        return sleepSamples
    }

    func fetchTodayStepTotal() async throws -> Int {
        if let error { throw error }
        return stepTotal
    }
}
