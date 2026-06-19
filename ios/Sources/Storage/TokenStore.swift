import Foundation
import Security

protocol TokenStore {
    func load() -> String?
    func save(_ token: String)
    func saveUsername(_ username: String)
    func loadUsername() -> String?
    func clear()
}

/// For tests and previews.
final class InMemoryTokenStore: TokenStore {
    private var token: String?
    private var storedUsername: String?
    init(_ token: String? = nil) { self.token = token }
    func load() -> String? { token }
    func save(_ token: String) { self.token = token }
    func saveUsername(_ username: String) { storedUsername = username }
    func loadUsername() -> String? { storedUsername }
    func clear() { token = nil; storedUsername = nil }
}

/// Stores the auth token and username in the iOS Keychain.
final class KeychainTokenStore: TokenStore {
    private let service = "com.synzoia.ios"
    private let tokenAccount = "auth-token"
    private let usernameAccount = "username"

    private func query(account: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }

    private func readItem(account: String) -> String? {
        var q = query(account: account)
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        let status = SecItemCopyMatching(q as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private func writeItem(account: String, value: String) {
        SecItemDelete(query(account: account) as CFDictionary)
        var attributes = query(account: account)
        attributes[kSecValueData as String] = Data(value.utf8)
        SecItemAdd(attributes as CFDictionary, nil)
    }

    func load() -> String? { readItem(account: tokenAccount) }

    func save(_ token: String) { writeItem(account: tokenAccount, value: token) }

    func saveUsername(_ username: String) { writeItem(account: usernameAccount, value: username) }

    func loadUsername() -> String? { readItem(account: usernameAccount) }

    func clear() {
        SecItemDelete(query(account: tokenAccount) as CFDictionary)
        SecItemDelete(query(account: usernameAccount) as CFDictionary)
    }
}
