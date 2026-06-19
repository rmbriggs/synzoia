import Foundation

struct CreateProfileResponse: Decodable, Equatable {
    let username: String
    let token: String
    let joinDate: String
}

struct CreateProfileRequest: Encodable {
    let username: String
}

struct FeedResponse: Decodable, Equatable {
    let posts: [Post]
}

struct Post: Decodable, Equatable, Identifiable {
    let id: Int
    let userId: Int
    let username: String
    let type: String
    let timestamp: String
    let details: PostDetails?
    let body: String?
}

/// Per-type feed details. All fields optional because the shape varies
/// by post type (sleep, steps, steps_milestone, leaderboard_recap, workout).
struct PostDetails: Decodable, Equatable {
    let nightOf: String?
    let durationMin: Int?
    let threshold: Int?
    let date: String?
    let top: [RecapEntry]?
}

struct RecapEntry: Decodable, Equatable {
    let username: String
    let total: Int
}
