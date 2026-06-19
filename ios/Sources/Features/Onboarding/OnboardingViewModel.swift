import Foundation
import Observation

@MainActor
@Observable
final class OnboardingViewModel {
    enum State: Equatable {
        case idle
        case submitting
        case failed(String)
    }

    var username: String = ""
    private(set) var state: State = .idle
    private(set) var mintedToken: String?

    private let api: APIClient
    private let onSignIn: (String) -> Void

    init(api: APIClient, onSignIn: @escaping (String) -> Void) {
        self.api = api
        self.onSignIn = onSignIn
    }

    var canSubmit: Bool {
        !username.trimmingCharacters(in: .whitespaces).isEmpty && state != .submitting
    }

    func join() async {
        let name = username.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }
        state = .submitting
        do {
            let profile = try await api.createProfile(username: name)
            mintedToken = profile.token
            state = .idle
            onSignIn(profile.token)
        } catch let error as APIError {
            state = .failed(error.userMessage)
        } catch {
            state = .failed("Something went wrong. Try again.")
        }
    }
}
