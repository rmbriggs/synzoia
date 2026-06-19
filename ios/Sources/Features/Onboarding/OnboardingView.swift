import SwiftUI

struct OnboardingView: View {
    @State private var model: OnboardingViewModel

    init(api: APIClient, onSignIn: @escaping (_ token: String, _ username: String) -> Void) {
        _model = State(initialValue: OnboardingViewModel(api: api, onSignIn: onSignIn))
    }

    var body: some View {
        ZStack {
            SynColor.bg.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {

                    // MARK: Headline
                    (Text("Join the\nmovement on\nsyn")
                        .foregroundStyle(SynColor.fg)
                     + Text("z")
                        .foregroundStyle(SynColor.primary)
                     + Text("oia")
                        .foregroundStyle(SynColor.fg))
                        .font(SynFont.serif(30, weight: .semibold, italic: true))
                        .tracking(-0.3)
                        .lineSpacing(2)
                        .padding(.top, 32)

                    // MARK: Body paragraph
                    Text("Pick a handle. We mint a token, store it securely on this phone, and your steps and sleep show up here automatically.")
                        .font(SynFont.sans(13.5))
                        .foregroundStyle(SynColor.muted)
                        .lineSpacing(4)
                        .padding(.top, 14)
                        .padding(.bottom, 24)

                    // MARK: Handle label
                    MonoLabel("Your handle")
                        .padding(.bottom, 8)

                    // MARK: Handle field
                    HStack(spacing: 4) {
                        Text("@")
                            .font(SynFont.serif(20, italic: true))
                            .foregroundStyle(SynColor.muted)

                        TextField("", text: $model.username)
                            .font(SynFont.serif(20, italic: true))
                            .foregroundStyle(SynColor.fg)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .tint(SynColor.primary)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 14)
                    .background(SynColor.card)
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(SynColor.primary, lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 14))
                    .padding(.bottom, 16)

                    // MARK: Error
                    if case .failed(let message) = model.state {
                        Text(message)
                            .font(SynFont.sans(13))
                            .foregroundStyle(.red)
                            .padding(.bottom, 8)
                    }

                    // MARK: Claim button
                    Button {
                        Task { await model.join() }
                    } label: {
                        ZStack {
                            if model.state == .submitting {
                                ProgressView()
                                    .tint(SynColor.primaryFg)
                            } else {
                                let handle = model.username.trimmingCharacters(in: .whitespacesAndNewlines)
                                Text(handle.isEmpty ? "Claim @handle" : "Claim @\(handle)")
                                    .font(SynFont.sans(15, weight: .bold))
                                    .foregroundStyle(SynColor.primaryFg)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 15)
                        .background(model.canSubmit ? SynColor.primary : SynColor.primary.opacity(0.45))
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                    }
                    .disabled(!model.canSubmit)
                    .padding(.bottom, 22)

                    // MARK: Numbered steps
                    StepRow(number: "1", text: "Claim your handle.")
                    StepRow(number: "2", text: "We store your token securely on this phone.", topPadding: 14)
                    StepRow(number: "3", text: "Walk and sleep. You're on the board.", topPadding: 14)

                    Spacer(minLength: 40)
                }
                .padding(.horizontal, 22)
            }
        }
    }
}

// MARK: - StepRow

private struct StepRow: View {
    let number: String
    let text: String
    var topPadding: CGFloat = 0

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            ZStack {
                Circle()
                    .fill(SynColor.accent)
                    .frame(width: 24, height: 24)
                Text(number)
                    .font(SynFont.mono(11, bold: true))
                    .foregroundStyle(SynColor.fg)
            }
            .padding(.top, 2)

            Text(text)
                .font(SynFont.sans(13))
                .foregroundStyle(SynColor.muted)
                .lineSpacing(3)
        }
        .padding(.top, topPadding)
    }
}

#Preview {
    OnboardingView(api: APIClient(config: .production), onSignIn: { _, _ in })
}
