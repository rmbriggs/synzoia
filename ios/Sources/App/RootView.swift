import SwiftUI

struct RootView: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        if app.isSignedIn {
            SignedInView(app: app)
        } else {
            OnboardingView(api: app.api, onSignIn: { token in
                app.signIn(token: token)
            })
        }
    }
}
