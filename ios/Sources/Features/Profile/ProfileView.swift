import SwiftUI

struct ProfileView: View {
    @State private var model: ProfileViewModel
    private let onOpenSettings: () -> Void

    init(api: APIClient, username: String, onOpenSettings: @escaping () -> Void) {
        _model = State(initialValue: ProfileViewModel(api: api, username: username))
        self.onOpenSettings = onOpenSettings
    }

    var body: some View {
        ZStack {
            SynColor.bg.ignoresSafeArea()
            content
        }
        .task { await model.load() }
    }

    // MARK: - Content

    @ViewBuilder
    private var content: some View {
        switch model.state {
        case .loading:
            VStack {
                coverBand(summary: nil)
                Spacer()
                ProgressView().tint(SynColor.primary)
                Spacer()
            }

        case .failed(let message):
            VStack {
                coverBand(summary: nil)
                Spacer()
                VStack(spacing: 12) {
                    Text(message)
                        .font(SynFont.mono(12))
                        .foregroundStyle(SynColor.muted)
                        .multilineTextAlignment(.center)
                    Button("Try again") { Task { await model.load() } }
                        .font(SynFont.mono(11))
                        .foregroundStyle(SynColor.primary)
                }
                .padding(.horizontal, 32)
                Spacer()
            }

        case .loaded:
            ScrollView {
                VStack(spacing: 0) {
                    coverBand(summary: model.stepsSummary)
                    VStack(spacing: 14) {
                        statsRow
                        weekCard
                        healthRow
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 20)
                    .padding(.bottom, 32)
                }
            }
            .scrollContentBackground(.hidden)
        }
    }

    // MARK: - Cover band + avatar header

    private func coverBand(summary: UserMetricSummary?) -> some View {
        ZStack(alignment: .bottom) {
            // Gradient cover band (~128pt)
            LinearGradient(
                stops: [
                    .init(color: SynColor.primary.opacity(0.45), location: 0),
                    .init(color: SynColor.fern.opacity(0.30), location: 0.55),
                    .init(color: SynColor.accent.opacity(0.15), location: 1)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .frame(height: 128)
            .overlay(
                RadialGradient(
                    colors: [SynColor.primary.opacity(0.18), Color.clear],
                    center: .topLeading,
                    startRadius: 0,
                    endRadius: 180
                )
            )

            // Avatar overlapping the cover bottom edge
            VStack(spacing: 0) {
                GradientAvatar(username: model.username, size: 78)
                    .overlay(
                        Circle()
                            .stroke(SynColor.bg, lineWidth: 3)
                    )
                    .padding(.top, 0)

                // "@username"
                Text("@\(model.username)")
                    .font(SynFont.serif(26, weight: .semibold))
                    .foregroundStyle(SynColor.fg)
                    .padding(.top, 10)

                // "JOINED JAN 2026 . 412,800 STEPS" or just "JOINED JAN 2026"
                MonoLabel(joinedLabel(summary: summary), size: 11, color: SynColor.muted)
                    .padding(.top, 4)
                    .padding(.bottom, 8)
            }
            .frame(maxWidth: .infinity)
            .offset(y: 78)
        }
        .frame(maxWidth: .infinity)
        .padding(.bottom, 78)
    }

    // MARK: - Stats row: 30-day score + Rank

    private var statsRow: some View {
        HStack(spacing: 12) {
            SynCard {
                VStack(alignment: .leading, spacing: 6) {
                    MonoLabel("30-day score", size: 10)
                    Text(scoreText)
                        .font(SynFont.serif(38, weight: .semibold))
                        .foregroundStyle(SynColor.fg)
                        .lineLimit(1)
                        .minimumScaleFactor(0.6)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            SynCard {
                VStack(alignment: .leading, spacing: 6) {
                    MonoLabel("rank", size: 10)
                    Text(rankText)
                        .font(SynFont.serif(38, weight: .semibold))
                        .foregroundStyle(SynColor.fg)
                        .lineLimit(1)
                        .minimumScaleFactor(0.6)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    // MARK: - This week card

    private var weekCard: some View {
        SynCard {
            VStack(alignment: .leading, spacing: 12) {
                MonoLabel("this week", size: 10)
                WeekBars(values: normalizedWeekValues)
                HStack {
                    ForEach(weekDayLabels, id: \.self) { label in
                        Text(label)
                            .font(SynFont.mono(8))
                            .foregroundStyle(SynColor.muted)
                            .frame(maxWidth: .infinity)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    // MARK: - Apple Health row

    private var healthRow: some View {
        Button(action: onOpenSettings) {
            HStack(spacing: 14) {
                ZStack {
                    Circle()
                        .fill(SynColor.healthRed.opacity(0.15))
                        .frame(width: 36, height: 36)
                    Image(systemName: "heart.fill")
                        .font(.system(size: 16, weight: .medium))
                        .foregroundStyle(SynColor.healthRed)
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text("Apple Health connected")
                        .font(SynFont.sans(15, weight: .semibold))
                        .foregroundStyle(SynColor.fg)
                    Text("Steps and sleep sync automatically")
                        .font(SynFont.mono(10))
                        .foregroundStyle(SynColor.muted)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(SynColor.muted)
            }
            .padding(15)
            .background(
                RoundedRectangle(cornerRadius: 18)
                    .fill(SynColor.card)
                    .overlay(
                        RoundedRectangle(cornerRadius: 18)
                            .stroke(SynColor.primary.opacity(0.28), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Helpers

    private func joinedLabel(summary: UserMetricSummary?) -> String {
        var parts: [String] = []

        if let joinDate = summary?.joinDate,
           let date = ProfileView.isoDateFormatter.date(from: joinDate) {
            let monthYear = ProfileView.monthYearFormatter.string(from: date)
            parts.append("JOINED \(monthYear.uppercased())")
        }

        if let score = summary?.score {
            parts.append(ProfileView.stepsFormatter.string(from: NSNumber(value: score)).map { "\($0) STEPS" } ?? "\(score) STEPS")
        }

        return parts.isEmpty ? "@\(model.username)" : parts.joined(separator: " \u{00B7} ")
    }

    private var scoreText: String {
        guard let score = model.stepsSummary?.score else { return "--" }
        return ProfileView.stepsFormatter.string(from: NSNumber(value: score)) ?? "\(score)"
    }

    private var rankText: String {
        guard let rank = model.stepsSummary?.rank else { return "--" }
        return "#\(rank)"
    }

    private var normalizedWeekValues: [Double] {
        let breakdown = model.stepsWeekly?.dailyBreakdown ?? []
        // Pad or trim to 7 values
        let totals: [Int]
        if breakdown.isEmpty {
            totals = Array(repeating: 0, count: 7)
        } else if breakdown.count >= 7 {
            totals = Array(breakdown.suffix(7).map { $0.total })
        } else {
            totals = Array(repeating: 0, count: 7 - breakdown.count) + breakdown.map { $0.total }
        }
        let maxVal = totals.max() ?? 0
        guard maxVal > 0 else {
            return Array(repeating: 0.08, count: 7) // minimal bar height when all zero
        }
        return totals.map { Double($0) / Double(maxVal) }
    }

    private var weekDayLabels: [String] {
        // Generate the last 7 day-of-week abbreviations
        let breakdown = model.stepsWeekly?.dailyBreakdown ?? []
        if breakdown.count >= 7 {
            return breakdown.suffix(7).map { entry -> String in
                guard let date = ProfileView.isoDateFormatter.date(from: entry.date) else { return "" }
                return ProfileView.dayFormatter.string(from: date).prefix(1).uppercased()
            }
        }
        // Fallback: generate from today backwards
        let cal = Calendar.current
        let today = Date()
        return (0..<7).reversed().map { offset -> String in
            guard let day = cal.date(byAdding: .day, value: -offset, to: today) else { return "" }
            return ProfileView.dayFormatter.string(from: day).prefix(1).uppercased()
        }
    }

    // MARK: - Static formatters

    private static let isoDateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.locale = Locale(identifier: "en_US_POSIX")
        return f
    }()

    private static let monthYearFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "MMM yyyy"
        f.locale = Locale(identifier: "en_US_POSIX")
        return f
    }()

    private static let dayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "EEE"
        f.locale = Locale(identifier: "en_US_POSIX")
        return f
    }()

    private static let stepsFormatter: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        return f
    }()
}

// MARK: - Preview

#Preview {
    ProfileView(
        api: APIClient(config: .production),
        username: "micah",
        onOpenSettings: {}
    )
}
