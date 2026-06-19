import Foundation
import Observation

@MainActor
@Observable
final class AppModel {
    private(set) var token: String?
    private let store: TokenStore

    /// Unauthenticated client for public reads and the public createProfile call.
    let api: APIClient

    init(store: TokenStore = KeychainTokenStore(), config: APIConfig = .production) {
        self.store = store
        self.token = store.load()
        self.api = APIClient(config: config)
    }

    var isSignedIn: Bool { token != nil }

    func signIn(token: String) {
        store.save(token)
        self.token = token
    }

    func signOut() {
        store.clear()
        self.token = nil
    }

    /// Client that carries the token, for Phase 2 sleep/steps writes.
    func authedClient() -> APIClient {
        api.withToken(token)
    }
}
