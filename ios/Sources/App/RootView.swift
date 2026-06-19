import SwiftUI

struct RootView: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        if app.isSignedIn {
            FeedView(api: app.api)
        } else {
            OnboardingView(api: app.api, onSignIn: { token in
                app.signIn(token: token)
            })
        }
    }
}
