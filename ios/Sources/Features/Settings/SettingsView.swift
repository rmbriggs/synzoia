import SwiftUI

struct SettingsView: View {
    let sync: SyncEngine
    let app: AppModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section("Apple Health") {
                    Button("Allow Apple Health access") {
                        Task { await sync.requestPermission() }
                    }
                    Button {
                        Task { await sync.syncNow() }
                    } label: {
                        if case .syncing = sync.status {
                            HStack { ProgressView(); Text("Syncing...") }
                        } else {
                            Text("Sync now")
                        }
                    }
                    .disabled(sync.status == .syncing)

                    if let lastResult = sync.lastResult {
                        Text(lastResult).font(.footnote).foregroundStyle(.secondary)
                    }
                    if case .failed(let message) = sync.status {
                        Text(message).font(.footnote).foregroundStyle(.red)
                    }
                }

                Section("Your token") {
                    Text(app.token ?? "Not signed in")
                        .font(.system(.footnote, design: .monospaced))
                        .textSelection(.enabled)
                    Text("Save this. It is the only way back into your account.")
                        .font(.caption).foregroundStyle(.secondary)
                }

                Section {
                    Button("Sign out", role: .destructive) {
                        app.signOut()
                        dismiss()
                    }
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
