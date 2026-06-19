import SwiftUI

/// The coastal dark palette. Values are the design's oklch tokens converted to sRGB.
enum SynColor {
    static func hex(_ s: String) -> Color {
        var h = s
        if h.hasPrefix("#") { h.removeFirst() }
        let v = UInt64(h, radix: 16) ?? 0
        return Color(.sRGB,
                     red: Double((v >> 16) & 0xFF) / 255,
                     green: Double((v >> 8) & 0xFF) / 255,
                     blue: Double(v & 0xFF) / 255,
                     opacity: 1)
    }

    static let bg = hex("#04110A")
    static let fg = hex("#E9E4DC")
    static let card = hex("#0E2017")
    static let card2 = hex("#16291F")
    static let muted = hex("#7B8B80")
    static let primary = hex("#2BD2C2")
    static let primaryFg = hex("#030E08")
    static let border = hex("#23382D")
    static let accent = hex("#21402C")
    static let fern = hex("#4CA871")
    static let amber = hex("#F6AC5C")
    static let bark = hex("#B97155")
    static let remPurple = hex("#807CC6")

    // avatar gradient stops
    static let teal = hex("#2BD2C2")
    static let deepTeal = hex("#00988C")
    static let deepFern = hex("#136239")
    static let amber2 = hex("#D28423")
    static let bark2 = hex("#723720")
    static let sky = hex("#30A4AA")
    static let healthRed = hex("#FA676E")

    /// Source stops the avatar gradients pick pairs from.
    static let avatarStops: [Color] = [teal, fern, deepTeal, deepFern, amber, amber2, bark, bark2, sky]
}
