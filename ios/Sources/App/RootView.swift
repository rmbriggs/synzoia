import SwiftUI

struct RootView: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        if app.isSignedIn {
            MainTabView(app: app)
        } else {
            OnboardingView(api: app.api, onSignIn: { token, username in
                app.signIn(token: token, username: username)
            })
        }
    }
}
