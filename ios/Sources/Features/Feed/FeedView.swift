import SwiftUI

struct FeedView: View {
    @State private var model: FeedViewModel
    private let onOpenSettings: (() -> Void)?

    init(api: APIClient, onOpenSettings: (() -> Void)? = nil) {
        _model = State(initialValue: FeedViewModel(api: api))
        self.onOpenSettings = onOpenSettings
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
            HStack(alignment: .center, spacing: 12) {
                SynWordmark(size: 25)
                Spacer()
                livePill
                Button {
                    onOpenSettings?()
                } label: {
                    GradientAvatar(username: "me", size: 34)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Settings")
            }
            .padding(.horizontal, 20)
            .padding(.top, 6)
            .padding(.bottom, 4)

            Text("Feed")
                .font(SynFont.serif(34, weight: .semibold))
                .foregroundStyle(SynColor.fg)
                .padding(.horizontal, 20)
                .padding(.top, 4)

            MonoLabel("Everyone's moving \u{00B7} today", size: 11, color: SynColor.muted)
                .padding(.horizontal, 20)
                .padding(.top, 7)
                .padding(.bottom, 14)
        }
        .background(SynColor.bg)
    }

    // MARK: - LIVE indicator

    private var livePill: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(SynColor.primary)
                .frame(width: 7, height: 7)
                .shadow(color: SynColor.primary, radius: 4)
            Text("LIVE")
                .font(SynFont.mono(10))
                .tracking(1.4)
                .foregroundStyle(SynColor.primary)
        }
    }

    // MARK: - Content

    @ViewBuilder
    private var content: some View {
        switch model.state {
        case .loading:
            Spacer()
            ProgressView()
                .tint(SynColor.primary)
            Spacer()
        case .empty:
            Spacer()
            VStack(spacing: 8) {
                Image(systemName: "moon.zzz")
                    .font(.system(size: 48))
                    .foregroundStyle(SynColor.muted)
                Text("No posts yet")
                    .font(SynFont.serif(22, weight: .semibold))
                    .foregroundStyle(SynColor.fg)
                Text("Posts from your crew will show up here.")
                    .font(SynFont.mono(11))
                    .foregroundStyle(SynColor.muted)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 32)
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
        case .loaded(let posts):
            List(posts) { post in
                PostRow(post: post)
                    .listRowBackground(SynColor.bg)
                    .listRowSeparator(.hidden)
                    .listRowInsets(EdgeInsets(top: 0, leading: 16, bottom: 14, trailing: 16))
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            .background(SynColor.bg)
            .refreshable { await model.refresh() }
        }
    }
}

#Preview {
    FeedView(api: APIClient(config: .production))
}
