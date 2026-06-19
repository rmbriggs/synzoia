import Foundation
import Observation

@MainActor
@Observable
final class ProfileViewModel {

    // MARK: - State

    enum State: Equatable {
        case loading
        case loaded
        case failed(String)
    }

    // MARK: - Published

    private(set) var state: State = .loading
    private(set) var stepsSummary: UserMetricSummary?
    private(set) var stepsWeekly: UserWeekly?

    // MARK: - Private

    private let api: APIClient
    let username: String

    // MARK: - Init

    init(api: APIClient, username: String) {
        self.api = api
        self.username = username
    }

    // MARK: - Load

    func load() async {
        state = .loading
        do {
            async let summaryResult = api.userSummary(.steps, username: username)
            async let weeklyResult = api.userWeekly(.steps, username: username)
            stepsSummary = try await summaryResult
            stepsWeekly = try await weeklyResult
            state = .loaded
        } catch let error as APIError {
            stepsSummary = nil
            stepsWeekly = nil
            state = .failed(error.userMessage)
        } catch {
            stepsSummary = nil
            stepsWeekly = nil
            state = .failed("Could not load profile.")
        }
    }
}
