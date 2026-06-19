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
    /// The entry for this user in the public profiles list, used for all-time steps + join date.
    private(set) var profileSummary: ProfileSummary?

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
            async let profilesResult = api.profiles()
            stepsSummary = try await summaryResult
            stepsWeekly = try await weeklyResult
            let profiles = try await profilesResult
            profileSummary = profiles.first { $0.username == username }
            state = .loaded
        } catch let error as APIError {
            stepsSummary = nil
            stepsWeekly = nil
            profileSummary = nil
            state = .failed(error.userMessage)
        } catch {
            stepsSummary = nil
            stepsWeekly = nil
            profileSummary = nil
            state = .failed("Could not load profile.")
        }
    }
}
