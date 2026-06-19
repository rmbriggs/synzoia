import SwiftUI

struct OnboardingView: View {
    @State private var model: OnboardingViewModel

    init(api: APIClient, onSignIn: @escaping (String) -> Void) {
        _model = State(initialValue: OnboardingViewModel(api: api, onSignIn: onSignIn))
    }

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Image(systemName: "moon.stars.fill").font(.system(size: 56))
            Text("synzoia").font(.largeTitle.bold())
            Text("Pick a username to join your crew.")
                .foregroundStyle(.secondary)

            TextField("username", text: $model.username)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .textFieldStyle(.roundedBorder)
                .padding(.horizontal, 40)

            if case .failed(let message) = model.state {
                Text(message).foregroundStyle(.red).font(.callout)
            }

            Button {
                Task { await model.join() }
            } label: {
                if model.state == .submitting {
                    ProgressView()
                } else {
                    Text("Join").bold().frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!model.canSubmit)
            .padding(.horizontal, 40)

            Spacer()
        }
        .padding()
    }
}

#Preview {
    OnboardingView(api: APIClient(config: .production), onSignIn: { _ in })
}
