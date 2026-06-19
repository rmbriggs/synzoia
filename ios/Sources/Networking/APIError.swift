import Foundation

enum APIError: Error, Equatable {
    case http(status: Int, code: String, message: String)
    case transport(String)
    case decoding(String)

    /// Safe to show in the UI.
    var userMessage: String {
        switch self {
        case .http(_, _, let message):
            return message
        case .transport:
            return "Network problem. Check your connection and try again."
        case .decoding:
            return "Unexpected response from the server."
        }
    }
}
