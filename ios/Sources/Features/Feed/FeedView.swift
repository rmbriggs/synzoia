import SwiftUI

struct FeedView: View {
    @State private var model: FeedViewModel
    private let onOpenSettings: (() -> Void)?

    init(api: APIClient, onOpenSettings: (() -> Void)? = nil) {
        _model = State(initialValue: FeedViewModel(api: api))
        self.onOpenSettings = onOpenSettings
    }

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Feed")
                .toolbar {
                    if let onOpenSettings {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button {
                                onOpenSettings()
                            } label: {
                                Image(systemName: "gearshape")
                            }
                            .accessibilityLabel("Settings")
                        }
                    }
                }
        }
        .task { await model.load() }
    }

    @ViewBuilder
    private var content: some View {
        switch model.state {
        case .loading:
            ProgressView("Loading feed...")
        case .empty:
            ContentUnavailableView("No posts yet", systemImage: "moon.zzz",
                                   description: Text("Posts from your crew will show up here."))
        case .failed(let message):
            VStack(spacing: 12) {
                Text(message).foregroundStyle(.secondary)
                Button("Try again") { Task { await model.load() } }
                    .buttonStyle(.bordered)
            }
        case .loaded(let posts):
            List(posts) { post in
                PostRow(post: post)
            }
            .listStyle(.plain)
            .refreshable { await model.refresh() }
        }
    }
}

#Preview {
    FeedView(api: APIClient(config: .production))
}
