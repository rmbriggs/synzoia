import SwiftUI

/// Brand type helpers. Three families:
///  - Serif:  Cormorant Garamond (variable, named-instance PS names confirmed to resolve)
///  - Mono:   Space Mono (static)
///  - Sans:   Plus Jakarta Sans (variable; the base PS names like "PlusJakartaSans-SemiBold"
///            do NOT resolve on iOS. The internal named-instance names like
///            "PlusJakartaSans-Regular_SemiBold" DO resolve and are used instead.)
enum SynFont {

    // MARK: - Serif (Cormorant Garamond)

    /// Returns a Cormorant Garamond font at the requested weight and slant.
    /// Cormorant Garamond is a variable font whose named instances have explicit
    /// PostScript names; all resolved correctly in font-resolution verification.
    static func serif(_ size: CGFloat, weight: Font.Weight = .semibold, italic: Bool = false) -> Font {
        let name: String
        switch (weight, italic) {
        case (.bold, false):    name = "CormorantGaramond-Bold"
        case (.bold, true):     name = "CormorantGaramond-BoldItalic"
        case (.semibold, true): name = "CormorantGaramond-SemiBoldItalic"
        case (.medium, true):   name = "CormorantGaramond-MediumItalic"
        case (_, true):         name = "CormorantGaramond-Italic"
        case (.medium, false):  name = "CormorantGaramond-Medium"
        default:                name = "CormorantGaramond-SemiBold"
        }
        return .custom(name, size: size)
    }

    // MARK: - Mono (Space Mono)

    /// Returns a Space Mono font (regular or bold).
    static func mono(_ size: CGFloat, bold: Bool = false) -> Font {
        .custom(bold ? "SpaceMono-Bold" : "SpaceMono-Regular", size: size)
    }

    // MARK: - Sans (Plus Jakarta Sans)

    /// Returns a Plus Jakarta Sans font at the requested weight.
    ///
    /// The brief's "PlusJakartaSans-SemiBold" style names do NOT resolve because
    /// the variable font's internal instance PS names use a "Regular_Weight" pattern.
    /// The actual names "PlusJakartaSans-Regular_SemiBold" etc. were verified via
    /// CTFontCollectionCreateMatchingFontDescriptors and are used here.
    static func sans(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        let name: String
        switch weight {
        case .bold, .heavy, .black:
            name = "PlusJakartaSans-Regular_Bold"
        case .semibold:
            name = "PlusJakartaSans-Regular_SemiBold"
        case .medium:
            name = "PlusJakartaSans-Regular_Medium"
        case .light:
            name = "PlusJakartaSans-Regular_Light"
        default:
            name = "PlusJakartaSans-Regular"
        }
        return .custom(name, size: size)
    }
}
