import SwiftUI

struct SettingsView: View {
    let sync: SyncEngine
    let app: AppModel
    @Environment(\.dismiss) private var dismiss

    @State private var copyConfirmed = false

    var body: some View {
        ZStack(alignment: .top) {
            SynColor.bg.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {

                    // MARK: Header
                    HStack(alignment: .center, spacing: 8) {
                        Button {
                            dismiss()
                        } label: {
                            ZStack {
                                Circle()
                                    .strokeBorder(SynColor.border, lineWidth: 1)
                                    .background(Circle().fill(SynColor.card))
                                    .frame(width: 34, height: 34)
                                Image(systemName: "xmark")
                                    .font(.system(size: 14, weight: .medium))
                                    .foregroundStyle(SynColor.fg)
                            }
                        }
                        .frame(width: 34, height: 34)

                        Text("Sync")
                            .font(SynFont.serif(22, weight: .semibold, italic: true))
                            .foregroundStyle(SynColor.fg)

                        Spacer()
                    }
                    .padding(.horizontal, 14)
                    .padding(.top, 8)
                    .padding(.bottom, 12)

                    // MARK: Content stack
                    VStack(spacing: 14) {

                        // MARK: Apple Health card
                        SynCard(padding: 16) {
                            HStack(alignment: .center, spacing: 13) {
                                ZStack {
                                    RoundedRectangle(cornerRadius: 12)
                                        .fill(SynColor.primary.opacity(0.16))
                                        .frame(width: 42, height: 42)
                                    Image(systemName: "heart.fill")
                                        .font(.system(size: 20))
                                        .foregroundStyle(SynColor.healthRed)
                                }
                                .frame(width: 42, height: 42)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Apple Health")
                                        .font(SynFont.sans(14, weight: .semibold))
                                        .foregroundStyle(SynColor.fg)
                                    Text("Steps · Sleep")
                                        .font(SynFont.mono(10))
                                        .foregroundStyle(SynColor.muted)
                                }

                                Spacer()

                                // Permission / On control
                                Button {
                                    Task { await sync.requestPermission() }
                                } label: {
                                    HStack(spacing: 5) {
                                        Circle()
                                            .fill(SynColor.primary)
                                            .frame(width: 6, height: 6)
                                        Text("On")
                                            .font(SynFont.mono(10))
                                            .tracking(1.0)
                                            .foregroundStyle(SynColor.primary)
                                    }
                                }
                                .buttonStyle(.plain)
                            }
                        }

                        // MARK: Sync now card
                        SynCard(padding: 16) {
                            VStack(alignment: .leading, spacing: 12) {
                                Button {
                                    Task { await sync.syncNow() }
                                } label: {
                                    HStack(spacing: 8) {
                                        if case .syncing = sync.status {
                                            ProgressView()
                                                .progressViewStyle(.circular)
                                                .tint(SynColor.primaryFg)
                                                .scaleEffect(0.85)
                                            Text("Syncing...")
                                                .font(SynFont.sans(14, weight: .semibold))
                                                .foregroundStyle(SynColor.primaryFg)
                                        } else {
                                            Text("Sync now")
                                                .font(SynFont.sans(14, weight: .semibold))
                                                .foregroundStyle(SynColor.primaryFg)
                                        }
                                    }
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 12)
                                    .background(SynColor.primary)
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                                }
                                .disabled(sync.status == .syncing)

                                if let lastResult = sync.lastResult {
                                    Text(lastResult)
                                        .font(SynFont.mono(11))
                                        .foregroundStyle(SynColor.muted)
                                }

                                if case .failed(let message) = sync.status {
                                    Text(message)
                                        .font(SynFont.mono(11))
                                        .foregroundStyle(SynColor.healthRed)
                                }

                                Text("synzoia reads Apple Health on this device and syncs on launch and when you tap Sync now.")
                                    .font(SynFont.sans(12.5))
                                    .foregroundStyle(SynColor.muted)
                                    .lineSpacing(4)
                            }
                        }

                        // MARK: Token card
                        ZStack {
                            RoundedRectangle(cornerRadius: 18)
                                .fill(SynColor.accent.opacity(0.5).blended(with: SynColor.card))
                            RoundedRectangle(cornerRadius: 18)
                                .strokeBorder(SynColor.border, lineWidth: 1)

                            VStack(alignment: .leading, spacing: 9) {
                                MonoLabel("Your token")

                                HStack(alignment: .center, spacing: 10) {
                                    Text(app.token ?? "Not signed in")
                                        .font(SynFont.mono(13))
                                        .foregroundStyle(SynColor.fg)
                                        .lineLimit(1)
                                        .truncationMode(.middle)
                                        .frame(maxWidth: .infinity, alignment: .leading)

                                    Button {
                                        if let token = app.token {
                                            UIPasteboard.general.string = token
                                            copyConfirmed = true
                                            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                                                copyConfirmed = false
                                            }
                                        }
                                    } label: {
                                        Text(copyConfirmed ? "Copied" : "Copy")
                                            .font(SynFont.mono(10))
                                            .tracking(0.8)
                                            .foregroundStyle(SynColor.primaryFg)
                                            .padding(.horizontal, 13)
                                            .padding(.vertical, 7)
                                            .background(SynColor.primary)
                                            .clipShape(RoundedRectangle(cornerRadius: 9))
                                    }
                                    .buttonStyle(.plain)
                                    .disabled(app.token == nil)
                                }

                                Text("Shown only here; the app never stores it elsewhere.")
                                    .font(SynFont.sans(12))
                                    .foregroundStyle(SynColor.muted)
                                    .lineSpacing(4)
                            }
                            .padding(16)
                        }

                        // MARK: Sign out
                        Button(role: .destructive) {
                            app.signOut()
                            dismiss()
                        } label: {
                            Text("Sign out")
                                .font(SynFont.sans(14, weight: .semibold))
                                .foregroundStyle(SynColor.healthRed)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                        }
                        .buttonStyle(.plain)
                    }
                    .padding(.horizontal, 16)
                    .padding(.bottom, 24)
                }
            }
        }
    }
}

// MARK: - Color blend helper (avoids iOS 17-only Color.mix)

private extension Color {
    /// Simple 50/50 sRGB blend. Used for the token card tint.
    func blended(with other: Color) -> Color {
        let a = UIColor(self)
        let b = UIColor(other)
        var r1: CGFloat = 0, g1: CGFloat = 0, b1: CGFloat = 0, a1: CGFloat = 0
        var r2: CGFloat = 0, g2: CGFloat = 0, b2: CGFloat = 0, a2: CGFloat = 0
        a.getRed(&r1, green: &g1, blue: &b1, alpha: &a1)
        b.getRed(&r2, green: &g2, blue: &b2, alpha: &a2)
        return Color(.sRGB,
                     red: (r1 + r2) / 2,
                     green: (g1 + g2) / 2,
                     blue: (b1 + b2) / 2,
                     opacity: (a1 + a2) / 2)
    }
}
