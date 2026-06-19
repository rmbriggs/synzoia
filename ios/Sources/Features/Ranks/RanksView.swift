import SwiftUI

struct RanksView: View {
    @State private var model: RanksViewModel
    private let onOpenDetail: (Metric) -> Void

    init(api: APIClient,
         currentUsername: String?,
         onOpenDetail: @escaping (Metric) -> Void) {
        _model = State(initialValue: RanksViewModel(api: api, currentUsername: currentUsername))
        self.onOpenDetail = onOpenDetail
    }

    var body: some View {
        ZStack {
            SynColor.bg.ignoresSafeArea()
            VStack(spacing: 0) {
                header
                content
            }
        }
        .task { await model.load() }
    }

    // MARK: - Header

    private var header: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Leaderboard")
                .font(SynFont.serif(34, weight: .semibold))
                .foregroundStyle(SynColor.fg)
                .padding(.horizontal, 20)
                .padding(.top, 8)
                .padding(.bottom, 4)

            MonoLabel("Rolling 30 days \u{00B7} capped", size: 11, color: SynColor.muted)
                .padding(.horizontal, 20)
                .padding(.bottom, 12)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(SynColor.bg)
    }

    // MARK: - Content

    @ViewBuilder
    private var content: some View {
        switch model.state {
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
                Button("Try again") { Task { await model.load() } }
                    .font(SynFont.mono(11))
                    .foregroundStyle(SynColor.primary)
            }
            .padding(.horizontal, 32)
            Spacer()

        case .loaded:
            ScrollView {
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    RankCategoryCard(
                        metric: .steps,
                        leader: model.leader(.steps),
                        myEntry: model.myEntry(.steps),
                        onTap: { onOpenDetail(.steps) }
                    )
                    RankCategoryCard(
                        metric: .sleep,
                        leader: model.leader(.sleep),
                        myEntry: model.myEntry(.sleep),
                        onTap: { onOpenDetail(.sleep) }
                    )
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 24)
            }
            .scrollContentBackground(.hidden)
            .background(SynColor.bg)
        }
    }
}

// MARK: - RankCategoryCard

private struct RankCategoryCard: View {
    let metric: Metric
    let leader: RankEntry?
    let myEntry: RankEntry?
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 0) {
                categoryLabel
                    .padding(.bottom, 11)

                if let leader {
                    leaderRow(leader)
                        .padding(.bottom, 9)
                }

                myRankLine
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(cardBackground)
            .overlay(
                RoundedRectangle(cornerRadius: 18)
                    .stroke(cardBorder, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 18))
        }
        .buttonStyle(.plain)
    }

    // MARK: Category header row

    private var categoryLabel: some View {
        HStack(spacing: 7) {
            Image(systemName: iconName)
                .font(.system(size: 14, weight: .light))
                .foregroundStyle(iconColor)
                .frame(width: 14, height: 14)

            MonoLabel(metricName, size: 10, color: SynColor.muted)
        }
    }

    // MARK: Leader row

    private func leaderRow(_ entry: RankEntry) -> some View {
        HStack(alignment: .center, spacing: 8) {
            GradientAvatar(username: entry.username, size: 30)

            VStack(alignment: .leading, spacing: 1) {
                Text("@\(entry.username)")
                    .font(SynFont.sans(13, weight: .semibold))
                    .foregroundStyle(SynColor.fg)
                    .lineLimit(1)

                MonoLabel(formattedRankValue(metric: metric, total: entry.total), size: 11, color: SynColor.muted)
            }
        }
    }

    // MARK: My rank line

    @ViewBuilder
    private var myRankLine: some View {
        if let me = myEntry {
            HStack(spacing: 0) {
                Text("You")
                    .font(SynFont.mono(10))
                    .foregroundStyle(SynColor.muted)
                Text(" \u{00B7} ")
                    .font(SynFont.mono(10))
                    .foregroundStyle(SynColor.muted)
                Text("#\(me.rank)")
                    .font(SynFont.mono(10))
                    .foregroundStyle(me.rank == 1 ? SynColor.primary : SynColor.fg)
            }
        } else {
            MonoLabel("You \u{00B7} unranked", size: 10, color: SynColor.muted)
        }
    }

    // MARK: Formatting

    private var metricName: String {
        switch metric {
        case .steps: return "Steps"
        case .sleep: return "Sleep"
        }
    }

    private var iconName: String {
        switch metric {
        case .steps: return "figure.walk"
        case .sleep: return "moon.fill"
        }
    }

    private var iconColor: Color {
        switch metric {
        case .steps: return SynColor.primary
        case .sleep: return SynColor.remPurple
        }
    }

    // MARK: Card appearance

    private var cardBackground: some ShapeStyle {
        switch metric {
        case .steps:
            // primary-tinted card: card 80% + primary 20% blend (matches design)
            return LinearGradient(
                colors: [SynColor.card2, SynColor.card],
                startPoint: .top,
                endPoint: .bottom
            )
        case .sleep:
            return LinearGradient(
                colors: [SynColor.card, SynColor.card],
                startPoint: .top,
                endPoint: .bottom
            )
        }
    }

    private var cardBorder: Color {
        switch metric {
        case .steps: return SynColor.primary.opacity(0.36)
        case .sleep: return SynColor.border
        }
    }
}

// MARK: - Preview

#Preview {
    RanksView(
        api: APIClient(config: .production),
        currentUsername: "micah",
        onOpenDetail: { _ in }
    )
}
