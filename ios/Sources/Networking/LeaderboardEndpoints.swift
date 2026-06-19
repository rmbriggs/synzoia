import Foundation

// MARK: - Metric

enum Metric {
    case steps
    case sleep

    var path: String {
        switch self {
        case .steps: return "steps"
        case .sleep: return "sleep"
        }
    }
}

// MARK: - Models

struct RankEntry: Decodable, Equatable {
    let rank: Int
    let username: String
    let total: Int
}

struct DailyTotal: Decodable, Equatable {
    let date: String
    let total: Int
}

struct RankingResponse: Decodable, Equatable {
    let weekStart: String
    let weekEnd: String
    let leaderboard: [RankEntry]
    let dailyBreakdown: [DailyTotal]
}

struct BestEntry: Decodable, Equatable {
    let date: String
    let total: Int
}

struct UserMetricSummary: Decodable, Equatable {
    let username: String
    let joinDate: String?
    let score: Int?
    let rank: Int?
    let best: BestEntry?

    // .convertFromSnakeCase turns best_day -> bestDay, best_night -> bestNight
    private enum CodingKeys: String, CodingKey {
        case username
        case joinDate
        case score
        case rank
        case bestDay
        case bestNight
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        username = try c.decode(String.self, forKey: .username)
        joinDate = try c.decodeIfPresent(String.self, forKey: .joinDate)
        score = try c.decodeIfPresent(Int.self, forKey: .score)
        rank = try c.decodeIfPresent(Int.self, forKey: .rank)
        let bestDay = try c.decodeIfPresent(BestEntry.self, forKey: .bestDay)
        let bestNight = try c.decodeIfPresent(BestEntry.self, forKey: .bestNight)
        best = bestDay ?? bestNight
    }
}

struct UserWeekly: Decodable, Equatable {
    let username: String
    let weeklyTotal: Int?
    let rankThisWeek: Int?
    let dailyBreakdown: [DailyTotal]
}

struct ProfileSummary: Decodable, Equatable {
    let username: String
    let joinDate: String
    let totalStepsAllTime: Int
}

struct ProfilesResponse: Decodable {
    let profiles: [ProfileSummary]
}

// MARK: - APIClient extensions

extension APIClient {
    func ranking(_ metric: Metric) async throws -> RankingResponse {
        try await get("/api/\(metric.path)/ranking")
    }

    func userSummary(_ metric: Metric, username: String) async throws -> UserMetricSummary {
        let encoded = username.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? username
        return try await get("/api/\(metric.path)/users/\(encoded)/summary")
    }

    func userWeekly(_ metric: Metric, username: String) async throws -> UserWeekly {
        let encoded = username.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? username
        return try await get("/api/\(metric.path)/users/\(encoded)/weekly")
    }

    func profiles() async throws -> [ProfileSummary] {
        let response: ProfilesResponse = try await get("/api/profiles")
        return response.profiles
    }
}
