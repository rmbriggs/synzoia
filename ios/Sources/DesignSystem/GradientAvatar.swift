import SwiftUI

enum AvatarStyle {
    static func initials(_ username: String) -> String {
        let cleaned = username.hasPrefix("@") ? String(username.dropFirst()) : username
        let letters = cleaned.filter { $0.isLetter || $0.isNumber }
        if letters.isEmpty { return "?" }
        return String(letters.prefix(2)).uppercased()
    }

    /// Deterministic 2-stop gradient chosen from the palette by hashing the name.
    static func gradient(_ username: String) -> [Color] {
        let stops = SynColor.avatarStops
        var h = 5381
        for b in username.utf8 { h = ((h << 5) &+ h) &+ Int(b) }
        let a = abs(h) % stops.count
        let b = (a + 3) % stops.count
        return [stops[a], stops[b]]
    }
}

struct GradientAvatar: View {
    let username: String
    var size: CGFloat = 32

    var body: some View {
        let stops = AvatarStyle.gradient(username)
        Circle()
            .fill(LinearGradient(colors: stops, startPoint: .topLeading, endPoint: .bottomTrailing))
            .frame(width: size, height: size)
            .overlay(
                Text(AvatarStyle.initials(username))
                    .font(SynFont.sans(size * 0.36, weight: .semibold))
                    .foregroundStyle(.white)
            )
    }
}

#Preview {
    HStack {
        GradientAvatar(username: "micah")
        GradientAvatar(username: "angela")
        GradientAvatar(username: "peter")
    }
    .padding().background(SynColor.bg)
}
