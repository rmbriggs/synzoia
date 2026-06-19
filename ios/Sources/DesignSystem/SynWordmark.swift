import SwiftUI

/// The "synzoia" logotype: serif italic with the "z" in teal (brand primary).
struct SynWordmark: View {
    var size: CGFloat = 25

    var body: some View {
        (Text("syn").foregroundStyle(SynColor.fg)
         + Text("z").foregroundStyle(SynColor.primary)
         + Text("oia").foregroundStyle(SynColor.fg))
            .font(SynFont.serif(size, weight: .semibold, italic: true))
            .tracking(-0.5)
    }
}

#Preview {
    SynWordmark()
        .padding()
        .background(SynColor.bg)
}
