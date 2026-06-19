import SwiftUI

// MARK: - Tab

private enum Tab: String {
    case feed
    case groups
    case ranks
    case you
}

// MARK: - MainTabView

/// 4-tab coastal shell: Feed / Groups / Ranks / You.
/// Owns the SyncEngine (absorbs SignedInView's role), presents Settings as a sheet.
struct MainTabView: View {

    let app: AppModel

    @State private var sync: SyncEngine
    @State private var selected: Tab
    @State private var showSettings = false
    @State private var ranksPath: [Metric] = []

    init(app: AppModel) {
        self.app = app
        _sync = State(initialValue: SyncEngine(health: HealthKitReader(), api: app.authedClient()))

        #if targetEnvironment(simulator)
        let startTab: Tab
        switch ProcessInfo.processInfo.environment["SYNZOIA_START_TAB"] {
        case "groups": startTab = .groups
        case "ranks":  startTab = .ranks
        case "you":    startTab = .you
        default:       startTab = .feed
        }
        _selected = State(initialValue: startTab)
        #else
        _selected = State(initialValue: .feed)
        #endif
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            tabContent
                .ignoresSafeArea(edges: .bottom)

            tabBar
        }
        .sheet(isPresented: $showSettings) {
            SettingsView(sync: sync, app: app)
        }
        .task {
            await sync.requestPermission()
            await sync.syncNow()
        }
    }

    // MARK: - Tab content

    @ViewBuilder
    private var tabContent: some View {
        switch selected {
        case .feed:
            FeedView(api: app.api, username: app.username, onOpenSettings: { showSettings = true })

        case .groups:
            GroupsView()

        case .ranks:
            NavigationStack(path: $ranksPath) {
                RanksView(
                    api: app.api,
                    currentUsername: app.username,
                    onOpenDetail: { metric in ranksPath.append(metric) }
                )
                .navigationDestination(for: Metric.self) { metric in
                    RankDetailView(
                        api: app.api,
                        currentUsername: app.username,
                        metric: metric,
                        onBack: { ranksPath.removeLast() }
                    )
                }
            }

        case .you:
            ProfileView(
                api: app.api,
                username: app.username ?? "",
                onOpenSettings: { showSettings = true }
            )
        }
    }

    // MARK: - Custom tab bar

    private var tabBar: some View {
        VStack(spacing: 0) {
            // Top border
            Rectangle()
                .fill(SynColor.border)
                .frame(height: 1)

            // Bar body: dark blurred background
            HStack(spacing: 0) {
                tabItem(.feed,   icon: "dot.radiowaves.up.forward", label: "Feed")
                tabItem(.groups, icon: "person.2",                  label: "Groups")
                tabItem(.ranks,  icon: "trophy",                    label: "Ranks")
                tabItem(.you,    icon: "person.crop.circle",        label: "You")
            }
            .padding(.top, 9)
            .padding(.bottom, 6)
            .padding(.horizontal, 14)
            .background(
                SynColor.card.opacity(0.82)
                    .background(.ultraThinMaterial)
            )
        }
    }

    private func tabItem(_ tab: Tab, icon: String, label: String) -> some View {
        let isActive = selected == tab
        return Button {
            if selected == tab, tab == .ranks {
                ranksPath = []
            }
            selected = tab
        } label: {
            VStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: 22, weight: .light))
                    .foregroundStyle(isActive ? SynColor.primary : SynColor.muted)

                Text(label)
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(isActive ? SynColor.primary : SynColor.muted)
            }
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .animation(.easeInOut(duration: 0.15), value: selected)
    }
}

// MARK: - Preview

#Preview {
    MainTabView(app: AppModel())
}
