import Foundation

final class APIClient {
    private let config: APIConfig
    private let session: URLSession
    private let token: String?

    init(config: APIConfig, session: URLSession = .shared, token: String? = nil) {
        self.config = config
        self.session = session
        self.token = token
    }

    /// Returns a copy of this client carrying the given token.
    func withToken(_ token: String?) -> APIClient {
        APIClient(config: config, session: session, token: token)
    }

    func get<T: Decodable>(_ path: String, query: [URLQueryItem] = []) async throws -> T {
        try await send(path: path, method: "GET", query: query, body: nil)
    }

    func post<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        let data = try APIClient.encoder.encode(body)
        return try await send(path: path, method: "POST", query: [], body: data)
    }

    private func send<T: Decodable>(path: String, method: String, query: [URLQueryItem], body: Data?) async throws -> T {
        var components = URLComponents(url: config.baseURL, resolvingAgainstBaseURL: false)!
        components.path = path
        if !query.isEmpty { components.queryItems = query }
        guard let url = components.url else { throw APIError.transport("Could not build URL") }

        var request = URLRequest(url: url)
        request.httpMethod = method
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if let token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.transport(error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.transport("No HTTP response")
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIClient.decodeError(status: http.statusCode, data: data)
        }
        do {
            return try APIClient.decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(String(describing: error))
        }
    }

    private static func decodeError(status: Int, data: Data) -> APIError {
        if let wrapper = try? decoder.decode(BackendErrorWrapper.self, from: data) {
            return .http(status: status, code: wrapper.error.code, message: wrapper.error.message)
        }
        return .http(status: status, code: "unknown",
                     message: HTTPURLResponse.localizedString(forStatusCode: status))
    }

    static let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()

    static let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()
}

private struct BackendErrorWrapper: Decodable {
    struct Inner: Decodable { let code: String; let message: String }
    let error: Inner
}
