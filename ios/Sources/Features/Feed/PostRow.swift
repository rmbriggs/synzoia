import SwiftUI

struct PostRow: View {
    let post: Post

    var body: some View {
        switch post.type {
        case "leaderboard_recap":
            RecapCard(post: post)
        case "steps_milestone":
            MilestoneCard(post: post)
        case "sleep":
            SleepCard(post: post)
        case "workout":
            WorkoutCard(post: post)
        case "steps":
            StepsRow(post: post)
        default:
            GenericCard(post: post)
        }
    }
}

// MARK: - Recap card

private struct RecapCard: View {
    let post: Post

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header row
            HStack(alignment: .center) {
                HStack(spacing: 8) {
                    Image(systemName: "trophy")
                        .font(.system(size: 15, weight: .regular))
                        .foregroundStyle(SynColor.amber)
                    Text("Top 3 today")
                        .font(SynFont.serif(18, weight: .semibold, italic: true))
                        .foregroundStyle(SynColor.fg)
                }
                Spacer()
                MonoLabel(formattedTime(post.timestamp), size: 10, color: SynColor.muted)
            }
            .padding(.bottom, 12)

            // Ranked rows
            VStack(spacing: 9) {
                if let entries = post.details?.top, !entries.isEmpty {
                    ForEach(Array(entries.prefix(3).enumerated()), id: \.offset) { i, entry in
                        RecapRow(rank: i + 1, entry: entry)
                    }
                } else {
                    MonoLabel("No data", size: 11, color: SynColor.muted)
                }
            }
        }
        .padding(16)
        .background(
            LinearGradient(
                colors: [
                    SynColor.recapCardTop,
                    SynColor.card
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 20)
                .stroke(SynColor.fern.opacity(0.28), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 20))
    }
}

private struct RecapRow: View {
    let rank: Int
    let entry: RecapEntry

    var rankColor: Color {
        switch rank {
        case 1: return SynColor.amber
        case 2: return SynColor.muted
        default: return SynColor.bark
        }
    }

    var body: some View {
        HStack(spacing: 10) {
            Text("\(rank)")
                .font(SynFont.mono(13, bold: true))
                .foregroundStyle(rankColor)
                .frame(width: 16, alignment: .leading)
            GradientAvatar(username: entry.username, size: 28)
            Text("@\(entry.username)")
                .font(SynFont.sans(14, weight: .semibold))
                .foregroundStyle(SynColor.fg)
                .lineLimit(1)
            Spacer()
            Text(formattedSteps(entry.total))
                .font(SynFont.mono(14))
                .foregroundStyle(SynColor.fg)
        }
    }
}

// MARK: - Milestone card

private struct MilestoneCard: View {
    let post: Post

    var body: some View {
        HStack(alignment: .center, spacing: 11) {
            GradientAvatar(username: post.username, size: 30)
            Group {
                Text("@\(post.username)").font(SynFont.sans(13.5, weight: .semibold)).foregroundStyle(SynColor.fg)
                + Text(" hit a ").font(SynFont.sans(13.5)).foregroundStyle(SynColor.fg)
                + Text(thresholdText).font(SynFont.sans(13.5, weight: .semibold)).foregroundStyle(SynColor.fg)
                + Text(" step milestone").font(SynFont.sans(13.5)).foregroundStyle(SynColor.fg)
            }
            .lineLimit(2)
            Spacer(minLength: 4)
            Image(systemName: "trophy")
                .font(.system(size: 15, weight: .regular))
                .foregroundStyle(SynColor.amber)
                .flexibleFrame()
        }
        .padding(.horizontal, 15)
        .padding(.vertical, 13)
        .background(SynColor.card)
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(SynColor.border, lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var thresholdText: String {
        if let t = post.details?.threshold {
            return formattedSteps(t)
        }
        return "10,000"
    }
}

// MARK: - Sleep card

private struct SleepCard: View {
    let post: Post

    var body: some View {
        SynCard(padding: 15, radius: 18) {
            VStack(alignment: .leading, spacing: 0) {
                // Avatar row
                HStack(spacing: 10) {
                    GradientAvatar(username: post.username, size: 32)
                    Text("@\(post.username)")
                        .font(SynFont.sans(14, weight: .semibold))
                        .foregroundStyle(SynColor.fg)
                    Spacer()
                    MonoLabel(formattedTime(post.timestamp), size: 10, color: SynColor.muted)
                }
                .padding(.bottom, 10)

                // Duration
                HStack(alignment: .lastTextBaseline, spacing: 8) {
                    Text(durationText)
                        .font(SynFont.serif(30, weight: .semibold))
                        .foregroundStyle(SynColor.fg)
                    HStack(spacing: 5) {
                        Image(systemName: "moon")
                            .font(.system(size: 11))
                            .foregroundStyle(SynColor.primary)
                        MonoLabel("best this week", size: 11, color: SynColor.muted)
                    }
                }
                .padding(.bottom, 11)

                // Sleep stage bar
                SleepStageBar(rem: stageSplit.rem, core: stageSplit.core, deep: stageSplit.deep, awake: stageSplit.awake)

                // Stage labels
                HStack(spacing: 14) {
                    MonoLabel("REM", size: 9.5, color: SynColor.muted)
                    MonoLabel("CORE", size: 9.5, color: SynColor.muted)
                    MonoLabel("DEEP", size: 9.5, color: SynColor.muted)
                }
                .padding(.top, 7)
            }
        }
    }

    private var durationText: String {
        guard let mins = post.details?.durationMin else { return "---" }
        let h = mins / 60
        let m = mins % 60
        return String(format: "%dh %02dm", h, m)
    }

    private var stageSplit: (rem: Double, core: Double, deep: Double, awake: Double) {
        guard let total = post.details?.durationMin, total > 0 else {
            return (rem: 2.4, core: 4.2, deep: 1.6, awake: 0.4)
        }
        let t = Double(total)
        // Typical proportions: REM ~27%, CORE ~55%, DEEP ~13%, awake ~5%
        return (rem: t * 0.27, core: t * 0.55, deep: t * 0.13, awake: t * 0.05)
    }
}

// MARK: - Workout card

private struct WorkoutCard: View {
    let post: Post

    var body: some View {
        SynCard(padding: 15, radius: 18) {
            VStack(alignment: .leading, spacing: 0) {
                // Avatar row with Run pill
                HStack(spacing: 10) {
                    GradientAvatar(username: post.username, size: 32)
                    Text("@\(post.username)")
                        .font(SynFont.sans(14, weight: .semibold))
                        .foregroundStyle(SynColor.fg)
                    Spacer()
                    HStack(spacing: 5) {
                        Image(systemName: "figure.run")
                            .font(.system(size: 10))
                        Text("Run")
                            .font(SynFont.mono(9.5))
                            .tracking(1.0)
                    }
                    .foregroundStyle(SynColor.fg)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 3)
                    .background(SynColor.accent)
                    .clipShape(Capsule())
                }
                .padding(.bottom, 11)

                // Stats row
                if hasStats {
                    HStack(alignment: .lastTextBaseline, spacing: 6) {
                        Text(distanceText)
                            .font(SynFont.serif(26, weight: .semibold))
                            .foregroundStyle(SynColor.fg)
                        MonoLabel(detailText, size: 12, color: SynColor.muted)
                    }
                } else {
                    Text("logged a workout")
                        .font(SynFont.mono(12))
                        .foregroundStyle(SynColor.muted)
                }
            }
        }
    }

    private var hasStats: Bool {
        post.body != nil || post.details != nil
    }

    private var distanceText: String {
        post.body ?? "Workout"
    }

    private var detailText: String {
        ""
    }
}

// MARK: - Steps text row

private struct StepsRow: View {
    let post: Post

    var body: some View {
        HStack(alignment: .center, spacing: 11) {
            GradientAvatar(username: post.username, size: 26)
            Group {
                Text("@\(post.username)")
                    .font(SynFont.mono(12, bold: true))
                    .foregroundStyle(SynColor.fg)
                + Text(" \u{00B7} \(stepsText) steps today")
                    .font(SynFont.mono(12))
                    .foregroundStyle(SynColor.muted)
            }
            .lineLimit(1)
            Spacer(minLength: 4)
            MonoLabel(relativeTime(post.timestamp), size: 10, color: SynColor.muted)
        }
        .padding(.horizontal, 6)
        .padding(.vertical, 4)
    }

    private var stepsText: String {
        // steps posts carry count in body or details
        if let body = post.body, !body.isEmpty { return body }
        return "---"
    }
}

// MARK: - Generic card

private struct GenericCard: View {
    let post: Post

    var body: some View {
        SynCard(padding: 13, radius: 14) {
            HStack(spacing: 10) {
                GradientAvatar(username: post.username, size: 28)
                VStack(alignment: .leading, spacing: 2) {
                    Text("@\(post.username)")
                        .font(SynFont.sans(13, weight: .semibold))
                        .foregroundStyle(SynColor.fg)
                    Text(post.body ?? post.type)
                        .font(SynFont.mono(11))
                        .foregroundStyle(SynColor.muted)
                        .lineLimit(2)
                }
                Spacer()
            }
        }
    }
}

// MARK: - Helpers

private func formattedSteps(_ n: Int) -> String {
    let f = NumberFormatter()
    f.numberStyle = .decimal
    return f.string(from: NSNumber(value: n)) ?? "\(n)"
}

private func formattedTime(_ iso: String) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    var date = formatter.date(from: iso)
    if date == nil {
        formatter.formatOptions = [.withInternetDateTime]
        date = formatter.date(from: iso)
    }
    guard let d = date else { return "" }
    let out = DateFormatter()
    out.dateFormat = "h:mm a"
    return out.string(from: d)
}

private func relativeTime(_ iso: String) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    var date = formatter.date(from: iso)
    if date == nil {
        formatter.formatOptions = [.withInternetDateTime]
        date = formatter.date(from: iso)
    }
    guard let d = date else { return "" }
    let diff = Date().timeIntervalSince(d)
    if diff < 3600 {
        return "\(Int(diff / 60))m"
    } else if diff < 86400 {
        return "\(Int(diff / 3600))h"
    }
    return "\(Int(diff / 86400))d"
}

// MARK: - Layout helper

extension View {
    fileprivate func flexibleFrame() -> some View {
        self.fixedSize()
    }
}
