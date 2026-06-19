import Foundation

/// The app's read-only view of Apple Health. Abstracted so the orchestration
/// (SyncEngine) is unit-testable with a fake, and only one file imports HealthKit.
protocol HealthReading {
    func requestAuthorization() async throws
    func fetchSleepSamples(from start: Date, to end: Date) async throws -> [SleepSample]
    func fetchTodayStepTotal() async throws -> Int
}
