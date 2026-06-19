import Foundation
import Security

protocol TokenStore {
    func load() -> String?
    func save(_ token: String)
    func clear()
}

/// For tests and previews.
final class InMemoryTokenStore: TokenStore {
    private var token: String?
    init(_ token: String? = nil) { self.token = token }
    func load() -> String? { token }
    func save(_ token: String) { self.token = token }
    func clear() { token = nil }
}

/// Stores the single auth token in the iOS Keychain.
final class KeychainTokenStore: TokenStore {
    private let service = "com.synzoia.ios"
    private let account = "auth-token"

    private func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }

    func load() -> String? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func save(_ token: String) {
        SecItemDelete(baseQuery() as CFDictionary)
        var attributes = baseQuery()
        attributes[kSecValueData as String] = Data(token.utf8)
        SecItemAdd(attributes as CFDictionary, nil)
    }

    func clear() {
        SecItemDelete(baseQuery() as CFDictionary)
    }
}
