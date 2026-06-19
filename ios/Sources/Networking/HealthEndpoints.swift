import Foundation

struct SleepSession: Decodable, Equatable {
    let id: Int
    let userId: Int
    let sessionType: String
    let status: String
    let reviewFlag: Bool
    let sleepDate: String
    let onset: String
    let wake: String
    let timeInBedMin: Int
    let totalAsleepMin: Int
    let awakeMin: Int
    let coreMin: Int
    let deepMin: Int
    let remMin: Int
    let wakeups: Int
    let efficiency: Double
    let capturedAt: String
}

struct IngestSleepResponse: Decodable, Equatable {
    let sessions: [SleepSession]
}

struct CreateStepRequest: Encodable {
    let timestamp: String
    let total: Int
}

struct CreateStepResponse: Decodable, Equatable {
    let id: Int
    let userId: Int
    let timestamp: String
    let total: Int
}

extension APIClient {
    /// Posts a raw sleep sample window. Returns the persisted sessions (the
    /// backend returns only the single latest session, but that is enough to
    /// confirm success).
    func postSleep(_ payload: SleepPayload) async throws -> [SleepSession] {
        let response: IngestSleepResponse = try await post("/api/sleep", body: payload)
        return response.sessions
    }

    /// Posts today's cumulative step total. Backend keeps MAX per CT day, so
    /// re-posting is idempotent.
    func postSteps(timestamp: String, total: Int) async throws -> CreateStepResponse {
        try await post("/api/steps", body: CreateStepRequest(timestamp: timestamp, total: total))
    }
}
