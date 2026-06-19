import Foundation

extension APIClient {
    func createProfile(username: String) async throws -> CreateProfileResponse {
        try await post("/api/profiles", body: CreateProfileRequest(username: username))
    }

    func fetchFeed(limit: Int = 50) async throws -> [Post] {
        let response: FeedResponse = try await get(
            "/api/posts",
            query: [URLQueryItem(name: "limit", value: String(limit))]
        )
        return response.posts
    }
}
