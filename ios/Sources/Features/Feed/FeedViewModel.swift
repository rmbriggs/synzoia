import Foundation
import Observation

@MainActor
@Observable
final class FeedViewModel {
    enum State: Equatable {
        case loading
        case loaded([Post])
        case empty
        case failed(String)
    }

    private(set) var state: State = .loading
    private let api: APIClient

    init(api: APIClient) { self.api = api }

    func load() async {
        state = .loading
        await refresh()
    }

    func refresh() async {
        do {
            let posts = try await api.fetchFeed()
            state = posts.isEmpty ? .empty : .loaded(posts)
        } catch let error as APIError {
            state = .failed(error.userMessage)
        } catch {
            state = .failed("Could not load the feed.")
        }
    }
}
