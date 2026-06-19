import Foundation
import Observation

/// Reads Apple Health and posts sleep + steps to the backend. Observable so the
/// Settings screen can show progress. Sleep and steps are posted in one pass;
/// an empty sleep window is skipped (an empty body would be a 422).
@MainActor
@Observable
final class SyncEngine {
    enum Status: Equatable {
        case idle
        case syncing
        case success(Date)
        case failed(String)
    }

    private(set) var status: Status = .idle
    private(set) var lastResult: String?

    private let health: HealthReading
    private let api: APIClient
    private let zone: TimeZone
    private let now: () -> Date

    /// Look back this far for sleep, matching the existing Shortcut's window.
    private let sleepLookbackHours: Double = 36

    init(health: HealthReading, api: APIClient, zone: TimeZone = .current, now: @escaping () -> Date = { Date() }) {
        self.health = health
        self.api = api
        self.zone = zone
        self.now = now
    }

    func requestPermission() async {
        try? await health.requestAuthorization()
    }

    func syncNow() async {
        status = .syncing
        let capturedAt = now()
        var parts: [String] = []
        do {
            let start = capturedAt.addingTimeInterval(-sleepLookbackHours * 3600)
            let samples = try await health.fetchSleepSamples(from: start, to: capturedAt)
            if samples.isEmpty {
                parts.append("no new sleep")
            } else {
                let payload = HealthPayloadBuilder.buildSleepPayload(from: samples, capturedAt: capturedAt, zone: zone)
                let sessions = try await api.postSleep(payload)
                parts.append("sleep synced (\(sessions.count) session\(sessions.count == 1 ? "" : "s"))")
            }

            let total = try await health.fetchTodayStepTotal()
            let steps = HealthPayloadBuilder.buildSteps(total: total, capturedAt: capturedAt, zone: zone)
            _ = try await api.postSteps(timestamp: steps.timestamp, total: steps.total)
            parts.append("\(total) steps synced")

            status = .success(capturedAt)
            lastResult = parts.joined(separator: ", ")
        } catch let error as APIError {
            status = .failed(error.userMessage)
            lastResult = "Sync failed: \(error.userMessage)"
        } catch {
            status = .failed("Sync failed. Try again.")
            lastResult = "Sync failed. Try again."
        }
    }
}
