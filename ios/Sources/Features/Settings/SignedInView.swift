import SwiftUI

/// Shown when the user has a token. Owns the SyncEngine (built with the
/// authenticated client) and hosts the Feed plus the Settings sheet. Requests
/// Health permission and runs an initial sync when it first appears.
struct SignedInView: View {
    let app: AppModel
    @State private var sync: SyncEngine
    @State private var showSettings = false

    init(app: AppModel) {
        self.app = app
        _sync = State(initialValue: SyncEngine(health: HealthKitReader(), api: app.authedClient()))
    }

    var body: some View {
        FeedView(api: app.api, onOpenSettings: { showSettings = true })
            .sheet(isPresented: $showSettings) {
                SettingsView(sync: sync, app: app)
            }
            .task {
                await sync.requestPermission()
                await sync.syncNow()
            }
    }
}
