import Foundation
import Observation

@MainActor
@Observable
final class RanksViewModel {

    // MARK: - State

    enum State: Equatable {
        case loading
        case loaded
        case failed(String)
    }

    // MARK: - Published

    private(set) var state: State = .loading
    private(set) var stepsRanking: RankingResponse?
    private(set) var sleepRanking: RankingResponse?

    // MARK: - Private

    private let api: APIClient
    private let currentUsername: String?

    // MARK: - Init

    init(api: APIClient, currentUsername: String?) {
        self.api = api
        self.currentUsername = currentUsername
    }

    // MARK: - Load

    func load() async {
        state = .loading
        do {
            async let stepsResult = api.ranking(.steps)
            async let sleepResult = api.ranking(.sleep)
            stepsRanking = try await stepsResult
            sleepRanking = try await sleepResult
            state = .loaded
        } catch let error as APIError {
            state = .failed(error.userMessage)
        } catch {
            state = .failed("Could not load leaderboard.")
        }
    }

    // MARK: - Helpers

    /// Returns the rank-1 entry for the given metric, or nil if not yet loaded.
    func leader(_ metric: Metric) -> RankEntry? {
        ranking(for: metric)?.leaderboard.first
    }

    /// Returns the current user's entry for the given metric, or nil if not found.
    func myEntry(_ metric: Metric) -> RankEntry? {
        guard let username = currentUsername else { return nil }
        return ranking(for: metric)?.leaderboard.first { $0.username == username }
    }

    // MARK: - Private

    private func ranking(for metric: Metric) -> RankingResponse? {
        switch metric {
        case .steps: return stepsRanking
        case .sleep: return sleepRanking
        }
    }
}
