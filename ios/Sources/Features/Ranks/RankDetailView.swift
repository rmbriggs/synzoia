import SwiftUI

// MARK: - RankDetailView

struct RankDetailView: View {
    // MARK: - Dependencies
    let api: APIClient
    let currentUsername: String?
    let onBack: () -> Void

    // MARK: - State
    @State private var selected: Metric
    @State private var ranking: RankingResponse?
    @State private var loadState: LoadState = .loading

    private enum LoadState {
        case loading
        case loaded
        case failed(String)
    }

    // MARK: - Init
    init(api: APIClient,
         currentUsername: String?,
         metric: Metric,
         onBack: @escaping () -> Void) {
        self.api = api
        self.currentUsername = currentUsername
        self.onBack = onBack
        _selected = State(initialValue: metric)
    }

    // MARK: - Body
    var body: some View {
        ZStack {
            SynColor.bg.ignoresSafeArea()
            VStack(spacing: 0) {
                navBar
                content
            }
        }
        .task { await loadRanking(selected) }
        .onChange(of: selected) { newMetric in
            Task { await loadRanking(newMetric) }
        }
    }

    // MARK: - Navigation Bar

    private var navBar: some View {
        HStack(spacing: 10) {
            Button(action: onBack) {
                ZStack {
                    Circle()
                        .fill(SynColor.card)
                        .overlay(Circle().stroke(SynColor.border, lineWidth: 1))
                        .frame(width: 34, height: 34)
                    Image(systemName: "chevron.left")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(SynColor.fg)
                }
            }
            .buttonStyle(.plain)

            HStack(spacing: 8) {
                Image(systemName: selected == .steps ? "figure.walk" : "moon.fill")
                    .font(.system(size: 15, weight: .light))
                    .foregroundStyle(SynColor.primary)

                Text(selected == .steps ? "Steps" : "Sleep")
                    .font(SynFont.serif(22, weight: .semibold, italic: true))
                    .foregroundStyle(SynColor.fg)
            }

            Spacer()
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 8)
        .background(SynColor.bg)
    }

    // MARK: - Content

    @ViewBuilder
    private var content: some View {
        switch loadState {
        case .loading:
            Spacer()
            ProgressView().tint(SynColor.primary)
            Spacer()

        case .failed(let message):
            Spacer()
            VStack(spacing: 12) {
                Text(message)
                    .font(SynFont.mono(12))
                    .foregroundStyle(SynColor.muted)
                    .multilineTextAlignment(.center)
                Button("Try again") {
                    Task { await loadRanking(selected) }
                }
                .font(SynFont.mono(11))
                .foregroundStyle(SynColor.primary)
            }
            .padding(.horizontal, 32)
            Spacer()

        case .loaded:
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    segmentedToggle
                        .padding(.bottom, 20)

                    podium
                        .padding(.bottom, 20)

                    rankedList

                    cappedNote
                        .padding(.top, 16)
                        .padding(.bottom, 32)
                }
                .padding(.horizontal, 16)
            }
            .scrollContentBackground(.hidden)
            .background(SynColor.bg)
        }
    }

    // MARK: - Segmented Toggle

    private var segmentedToggle: some View {
        HStack(spacing: 6) {
            segmentButton(.steps, label: "Steps")
            segmentButton(.sleep, label: "Sleep")
        }
        .padding(4)
        .background(SynColor.card)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(SynColor.border, lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func segmentButton(_ metric: Metric, label: String) -> some View {
        let active = selected == metric
        return Button {
            selected = metric
        } label: {
            Text(label.uppercased())
                .font(SynFont.mono(10))
                .tracking(1.0)
                .fontWeight(active ? .bold : .regular)
                .foregroundStyle(active ? SynColor.primaryFg : SynColor.muted)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 7)
                .background(
                    Group {
                        if active {
                            RoundedRectangle(cornerRadius: 8)
                                .fill(SynColor.primary)
                        } else {
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.clear)
                        }
                    }
                )
        }
        .buttonStyle(.plain)
        .animation(.easeInOut(duration: 0.15), value: selected)
    }

    // MARK: - Podium

    private var podium: some View {
        let entries = ranking?.leaderboard ?? []
        let rank1 = entries.first { $0.rank == 1 }
        let rank2 = entries.first { $0.rank == 2 }
        let rank3 = entries.first { $0.rank == 3 }

        return HStack(alignment: .bottom, spacing: 10) {
            // #2 left
            podiumColumn(entry: rank2, rankNum: 2, columnHeight: 66, avatarSize: 44, isGold: false)
            // #1 center (tallest)
            podiumColumn(entry: rank1, rankNum: 1, columnHeight: 94, avatarSize: 56, isGold: true)
            // #3 right
            podiumColumn(entry: rank3, rankNum: 3, columnHeight: 52, avatarSize: 40, isGold: false)
        }
        .frame(maxWidth: .infinity)
    }

    @ViewBuilder
    private func podiumColumn(
        entry: RankEntry?,
        rankNum: Int,
        columnHeight: CGFloat,
        avatarSize: CGFloat,
        isGold: Bool
    ) -> some View {
        VStack(spacing: 0) {
            // Avatar
            let username = entry?.username ?? ""
            ZStack {
                if !username.isEmpty {
                    GradientAvatar(username: username, size: avatarSize)
                } else {
                    Circle()
                        .fill(SynColor.card)
                        .frame(width: avatarSize, height: avatarSize)
                }
            }
            .overlay(
                isGold
                    ? Circle().stroke(SynColor.amber, lineWidth: 3)
                    : Circle().stroke(Color.clear, lineWidth: 0)
            )
            .padding(.bottom, 8)

            // Podium block
            VStack(spacing: 2) {
                Text("\(rankNum)")
                    .font(SynFont.serif(isGold ? 26 : rankNum == 2 ? 20 : 18, weight: .bold))
                    .foregroundStyle(SynColor.fg)

                if let entry {
                    Text(formattedValue(entry.total))
                        .font(SynFont.mono(9))
                        .foregroundStyle(SynColor.muted)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: columnHeight)
            .padding(.top, isGold ? 10 : 8)
            .background(podiumBlockBackground(isGold: isGold))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(
                        isGold
                            ? SynColor.amber.opacity(0.4)
                            : SynColor.border,
                        lineWidth: 1
                    )
            )
            .clipShape(
                UnevenRoundedRectangle(
                    topLeadingRadius: 12,
                    bottomLeadingRadius: 0,
                    bottomTrailingRadius: 0,
                    topTrailingRadius: 12
                )
            )
        }
        .frame(maxWidth: .infinity)
    }

    private func podiumBlockBackground(isGold: Bool) -> some ShapeStyle {
        if isGold {
            // amber-tinted gradient for #1
            return LinearGradient(
                colors: [
                    SynColor.amber.opacity(0.26).blendedIntoCard,
                    SynColor.card
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        } else {
            return LinearGradient(
                colors: [SynColor.card, SynColor.card],
                startPoint: .top,
                endPoint: .bottom
            )
        }
    }

    // MARK: - Ranked List (rank 4+)

    @ViewBuilder
    private var rankedList: some View {
        let entries = (ranking?.leaderboard ?? []).filter { $0.rank >= 4 }
        ForEach(entries, id: \.rank) { entry in
            rankedRow(entry)
        }
    }

    private func rankedRow(_ entry: RankEntry) -> some View {
        let isMe = currentUsername.map { $0 == entry.username } ?? false
        return HStack(alignment: .center, spacing: 11) {
            Text("#\(entry.rank)")
                .font(SynFont.mono(13))
                .foregroundStyle(isMe ? SynColor.primary : SynColor.muted)
                .fontWeight(isMe ? .bold : .regular)
                .frame(width: 22, alignment: .leading)

            GradientAvatar(username: entry.username, size: 28)
                .overlay(
                    isMe
                        ? Circle().stroke(SynColor.primary, lineWidth: 2)
                        : Circle().stroke(Color.clear, lineWidth: 0)
                )

            Text("@\(entry.username)")
                .font(SynFont.sans(13.5, weight: isMe ? .bold : .semibold))
                .foregroundStyle(isMe ? SynColor.primary : SynColor.fg)
                .frame(maxWidth: .infinity, alignment: .leading)

            Text(formattedValue(entry.total))
                .font(SynFont.mono(13))
                .foregroundStyle(isMe ? SynColor.primary : SynColor.fg)
        }
        .padding(.vertical, 11)
        .padding(.horizontal, isMe ? 8 : 0)
        .background(
            isMe
                ? RoundedRectangle(cornerRadius: 12).fill(SynColor.primary.opacity(0.12))
                : RoundedRectangle(cornerRadius: 12).fill(Color.clear)
        )
        .padding(.horizontal, isMe ? -8 : 0)
        .overlay(
            !isMe
                ? Rectangle()
                    .fill(SynColor.border)
                    .frame(height: 1)
                    .frame(maxWidth: .infinity, alignment: .bottom)
                    .offset(y: 0)
                : nil,
            alignment: .bottom
        )
    }

    // MARK: - Capped Note

    private var cappedNote: some View {
        let text: String
        switch selected {
        case .steps:
            text = "Capped at 25k / day. Consistency beats one big day."
        case .sleep:
            text = "Rolling 30-day average. Quality and consistency count."
        }
        return Text(text.uppercased())
            .font(SynFont.mono(10))
            .tracking(0.9)
            .foregroundStyle(SynColor.muted)
            .lineSpacing(4)
            .padding(.horizontal, 4)
    }

    // MARK: - Data Loading

    @MainActor
    private func loadRanking(_ metric: Metric) async {
        loadState = .loading
        ranking = nil
        do {
            let result = try await api.ranking(metric)
            ranking = result
            loadState = .loaded
        } catch let error as APIError {
            loadState = .failed(error.userMessage)
        } catch {
            loadState = .failed("Could not load leaderboard.")
        }
    }

    // MARK: - Formatting

    private func formattedValue(_ total: Int) -> String {
        switch selected {
        case .steps:
            return Self.stepsFormatter.string(from: NSNumber(value: total)) ?? "\(total)"
        case .sleep:
            let hours = total / 60
            let minutes = total % 60
            return String(format: "%dh %02dm", hours, minutes)
        }
    }

    private static let stepsFormatter: NumberFormatter = {
        let f = NumberFormatter()
        f.numberStyle = .decimal
        return f
    }()
}

// MARK: - Color blend helper

private extension Color {
    /// Approximate amber blended into card (26% amber, 74% card) for the #1 podium top.
    /// Matches design: `color-mix(in oklch, amber 26%, card)`.
    var blendedIntoCard: Color {
        // SynColor.amber is #F6AC5C; 26% on top of card #0E2017
        // Resulting sRGB = 0.26 * (0.965, 0.675, 0.361) + 0.74 * (0.055, 0.126, 0.090)
        // ~ (0.292, 0.269, 0.160) -> #4A4429
        return SynColor.hex("#4A4429")
    }
}

// MARK: - Preview

#Preview {
    let mockRanking = RankingResponse(
        weekStart: "2026-06-01",
        weekEnd: "2026-06-30",
        leaderboard: [
            RankEntry(rank: 1, username: "micah", total: 412000),
            RankEntry(rank: 2, username: "angela", total: 388000),
            RankEntry(rank: 3, username: "anna", total: 355000),
            RankEntry(rank: 4, username: "peter", total: 331000),
            RankEntry(rank: 5, username: "dana", total: 298000),
            RankEntry(rank: 6, username: "jordan", total: 256000),
            RankEntry(rank: 7, username: "sam", total: 241000),
        ],
        dailyBreakdown: []
    )
    _ = mockRanking // suppress unused warning
    return RankDetailView(
        api: APIClient(config: .production),
        currentUsername: "sam",
        metric: .steps,
        onBack: {}
    )
}
