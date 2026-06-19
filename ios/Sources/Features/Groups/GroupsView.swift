import SwiftUI

struct GroupsView: View {
    var body: some View {
        ZStack {
            SynColor.bg.ignoresSafeArea()
            VStack(spacing: 0) {
                header
                Spacer()
                comingSoonCard
                Spacer()
            }
        }
    }

    // MARK: - Header

    private var header: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Groups")
                .font(SynFont.serif(34, weight: .semibold))
                .foregroundStyle(SynColor.fg)
                .padding(.horizontal, 20)
                .padding(.top, 8)
                .padding(.bottom, 4)

            MonoLabel("Your circles", size: 11, color: SynColor.muted)
                .padding(.horizontal, 20)
                .padding(.bottom, 12)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(SynColor.bg)
    }

    // MARK: - Coming soon card

    private var comingSoonCard: some View {
        SynCard(padding: 28) {
            VStack(spacing: 18) {
                ZStack {
                    Circle()
                        .fill(SynColor.primary.opacity(0.12))
                        .frame(width: 64, height: 64)
                    Image(systemName: "person.2")
                        .font(.system(size: 28, weight: .light))
                        .foregroundStyle(SynColor.primary)
                }

                VStack(spacing: 8) {
                    Text("Groups are coming")
                        .font(SynFont.serif(26, weight: .semibold))
                        .foregroundStyle(SynColor.fg)
                        .multilineTextAlignment(.center)

                    Text("Crews, challenges, and circles are on the way. For now everyone shares one feed and leaderboard.")
                        .font(SynFont.mono(12))
                        .foregroundStyle(SynColor.muted)
                        .multilineTextAlignment(.center)
                        .lineSpacing(4)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
        }
        .padding(.horizontal, 32)
    }
}

// MARK: - Preview

#Preview {
    GroupsView()
}
