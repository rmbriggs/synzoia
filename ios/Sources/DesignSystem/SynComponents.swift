import SwiftUI

// MARK: - SynCard

struct SynCard<Content: View>: View {
    var padding: CGFloat = 15
    var radius: CGFloat = 18
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .background(SynColor.card)
            .overlay(RoundedRectangle(cornerRadius: radius).stroke(SynColor.border, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: radius))
    }
}

// MARK: - MonoLabel

struct MonoLabel: View {
    let text: String
    var size: CGFloat = 11
    var color: Color = SynColor.muted

    init(_ text: String, size: CGFloat = 11, color: Color = SynColor.muted) {
        self.text = text
        self.size = size
        self.color = color
    }

    var body: some View {
        Text(text.uppercased())
            .font(SynFont.mono(size))
            .tracking(1.4)
            .foregroundStyle(color)
    }
}

// MARK: - Pill

struct Pill: View {
    let text: String
    var filled: Bool = false

    init(_ text: String, filled: Bool = false) {
        self.text = text
        self.filled = filled
    }

    var body: some View {
        Text(text)
            .font(SynFont.mono(10))
            .tracking(1.0)
            .foregroundStyle(filled ? SynColor.primary : SynColor.muted)
            .padding(.horizontal, 10).padding(.vertical, 3)
            .background(Capsule().fill(filled ? SynColor.primary.opacity(0.2) : .clear))
            .overlay(Capsule().stroke(SynColor.border, lineWidth: filled ? 0 : 1))
    }
}

// MARK: - SleepStageBar

/// Horizontal segmented bar showing sleep stage proportions.
/// Uses GeometryReader with explicit fractional widths so segments reliably
/// distribute by weight regardless of SwiftUI layout passes.
struct SleepStageBar: View {
    var rem: Double
    var core: Double
    var deep: Double
    var awake: Double

    var body: some View {
        GeometryReader { geo in
            let total = max(rem + core + deep + awake, 0.001)
            let gap: CGFloat = 2
            let gapTotal: CGFloat = gap * 3
            let available = geo.size.width - gapTotal

            HStack(spacing: gap) {
                segBar(fraction: rem / total, available: available, color: SynColor.remPurple)
                segBar(fraction: core / total, available: available, color: SynColor.primary)
                segBar(fraction: deep / total, available: available, color: SynColor.fern)
                segBar(fraction: awake / total, available: available, color: SynColor.muted)
            }
        }
        .frame(height: 8)
    }

    private func segBar(fraction: Double, available: CGFloat, color: Color) -> some View {
        Rectangle()
            .fill(color)
            .frame(width: max(available * CGFloat(fraction), 0))
    }
}

// MARK: - WeekBars

/// 7-day bar chart. Last bar is full primary; previous bars are primary at 55% opacity.
struct WeekBars: View {
    var values: [Double]            // 0...1 heights, 7 entries

    var body: some View {
        HStack(alignment: .bottom, spacing: 5) {
            ForEach(Array(values.enumerated()), id: \.offset) { i, v in
                RoundedRectangle(cornerRadius: 3)
                    .fill(i == values.count - 1 ? SynColor.primary : SynColor.primary.opacity(0.55))
                    .frame(maxWidth: .infinity)
                    .frame(height: max(6, CGFloat(v) * 56))
            }
        }
        .frame(height: 56)
    }
}

// MARK: - Previews

#Preview("SynCard") {
    SynCard {
        VStack(alignment: .leading, spacing: 8) {
            MonoLabel("Sleep Score")
            Text("87").font(SynFont.serif(48, weight: .semibold)).foregroundStyle(SynColor.fg)
            HStack { Pill("REM", filled: true); Pill("7h 14m") }
        }
    }
    .padding()
    .background(SynColor.bg)
}

#Preview("SleepStageBar") {
    SleepStageBar(rem: 90, core: 180, deep: 60, awake: 30)
        .padding()
        .background(SynColor.bg)
}

#Preview("WeekBars") {
    WeekBars(values: [0.6, 0.75, 0.5, 0.8, 0.65, 0.7, 0.9])
        .padding()
        .background(SynColor.bg)
}
