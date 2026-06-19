import SwiftUI

@main
struct SynzoiaApp: App {
    @State private var app = makeAppModel()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(app)
        }
    }
}

/// Builds the AppModel, injecting a token from the
/// `SYNZOIA_TOKEN` launch-environment variable when present.
/// Used only by simulator screenshots and UI automation.
@MainActor
private func makeAppModel() -> AppModel {
    let model = AppModel()
    #if targetEnvironment(simulator)
    if let token = ProcessInfo.processInfo.environment["SYNZOIA_TOKEN"], !token.isEmpty {
        model.signIn(token: token)
    }
    #endif
    return model
}
