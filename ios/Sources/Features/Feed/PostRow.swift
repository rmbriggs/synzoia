import SwiftUI

struct PostRow: View {
    let post: Post

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.title3)
                .frame(width: 28)
                .foregroundStyle(.tint)
            VStack(alignment: .leading, spacing: 2) {
                Text(post.username).font(.headline)
                Text(summary).font(.subheadline).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.vertical, 4)
    }

    private var icon: String {
        switch post.type {
        case "sleep": return "moon.fill"
        case "steps": return "figure.walk"
        case "steps_milestone": return "flag.checkered"
        case "leaderboard_recap": return "trophy.fill"
        case "workout": return "dumbbell.fill"
        default: return "sparkles"
        }
    }

    private var summary: String {
        switch post.type {
        case "sleep":
            if let mins = post.details?.durationMin {
                return "slept \(mins / 60)h \(mins % 60)m"
            }
            return "posted sleep"
        case "steps":
            return "logged steps"
        case "steps_milestone":
            if let t = post.details?.threshold {
                return "hit \(t) steps"
            }
            return "hit a steps milestone"
        case "leaderboard_recap":
            return "daily leaderboard recap"
        default:
            return post.body ?? post.type
        }
    }
}
