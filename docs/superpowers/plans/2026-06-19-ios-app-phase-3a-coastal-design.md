# synzoia iOS app: Phase 3A Plan (coastal design system + restyle existing screens)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Bring the app's look to the approved "coastal" design (`Synzoia App.dc.html`): bundle the three brand fonts, build the exact dark color palette and typography, build the reusable components (gradient avatars, cards), and restyle the three existing screens (Onboarding, Feed, Settings) to match. The 4-tab shell and the new Ranks/Profile/Groups screens are Phase 3B.

**Architecture:** A `DesignSystem/` group holds the palette (`SynColor`), typography (`SynFont` + the `SynWordmark` view), and reusable views (`GradientAvatar`, `SynCard`, `MonoLabel`, `Pill`, `SleepStageBar`, `WeekBars`). The three existing feature screens are restyled to consume those. No data-layer or backend changes in 3A (Feed already loads `GET /api/posts`; we only restyle its rendering).

**Tech Stack:** SwiftUI, bundled TTF fonts (Info.plist `UIAppFonts`), Observation, XCTest. Apple frameworks only, no SPM.

**Design source of truth:** `sdd/synzoia-app-design.html` (the full design canvas, in the git-excluded `sdd/` working dir). Implementers MUST open it to copy exact spacing, font sizes, radii, and structure for the screen they build. Screen markup line ranges are noted per task.

## Global Constraints

- **Platform/language:** iOS 17.0, Swift language mode 5.0, iPhone only, Apple frameworks only, NO SPM.
- **Worktree/branch:** work in `~/Developer/synzoia/.claude/worktrees/ios-app` on `feat/ios-app`. After adding files or editing `ios/project.yml`, run `cd ios && xcodegen generate && cd ..`.
- **Theme:** Dark only for v1 (the design's default). Do not implement the Light palette yet.
- **Exact dark palette (oklch converted to sRGB, use verbatim):**
  | token | hex | token | hex |
  |---|---|---|---|
  | bg | `#04110A` | primary | `#2BD2C2` |
  | fg | `#E9E4DC` | primaryFg | `#030E08` |
  | card | `#0E2017` | border | `#23382D` |
  | card2 | `#16291F` | accent | `#21402C` |
  | muted | `#7B8B80` | fern | `#4CA871` |
  | amber | `#F6AC5C` | bark | `#B97155` |
  | remPurple (sleep REM) | `#807CC6` | | |
  Avatar gradient stops (sRGB): teal `#2BD2C2`, fern `#4CA871`, deepTeal `#00988C`, deepFern `#136239`, amber2 `#D28423`, bark2 `#723720`, sky `#30A4AA`. Health-heart red `#FA676E`.
- **Fonts (bundle as TTF, register in Info.plist `UIAppFonts`):** Plus Jakarta Sans (sans/body, weights 400/500/600/700), Cormorant Garamond (serif headings + wordmark, 500/600/700 roman + italic), Space Mono (mono labels/numbers, 400/700). Refer to them by PostScript name via `Font.custom`.
- **Type roles (from the design):** serif = Cormorant Garamond, used italic for the wordmark and section headers; large screen titles use serif 600 ~34pt; mono = Space Mono, uppercase, letter-spaced, ~10-11pt for labels/timestamps/numbers; body = Plus Jakarta Sans 400-600.
- **No em dashes** anywhere (code, comments, commits). Commit bodies end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Verification:** build must be `** BUILD SUCCEEDED **`; existing 33 tests stay green; screen tasks also capture a simulator screenshot to compare against the design. Test simulator `iPhone 17`.

## File Structure (Phase 3A)

```
ios/
  Resources/Fonts/                       # NEW: bundled .ttf files
  Sources/
    Info.plist                           # MODIFY: UIAppFonts
    DesignSystem/
      SynColor.swift                     # palette
      SynFont.swift                      # font helpers + text styles
      SynWordmark.swift                  # the syn[z]oia wordmark view
      GradientAvatar.swift               # initials + deterministic gradient
      SynComponents.swift                # SynCard, MonoLabel, Pill, SleepStageBar, WeekBars
    Features/
      Onboarding/OnboardingView.swift    # MODIFY: restyle to the Join design
      Feed/FeedView.swift                # MODIFY: coastal shell + header
      Feed/PostRow.swift                 # MODIFY/REPLACE: design feed cards
      Settings/SettingsView.swift        # MODIFY: restyle to the Connect design (native-adapted)
  project.yml                            # MODIFY: add Resources/Fonts to sources
  Tests/
    GradientAvatarTests.swift            # NEW: initials + gradient determinism
```

---

### Task 1: Bundle the brand fonts

Deliverable: the three font families are bundled and registered, and a smoke build confirms the app still builds with the font resources present.

**Files:** Create `ios/Resources/Fonts/*.ttf`; modify `ios/Sources/Info.plist`; modify `ios/project.yml`.

- [ ] **Step 1: Download the TTFs into `ios/Resources/Fonts/`.** These are OFL-licensed Google Fonts (free to bundle). Run from the worktree root:

```bash
mkdir -p ios/Resources/Fonts && cd ios/Resources/Fonts
base="https://raw.githubusercontent.com/google/fonts/main/ofl"
# Plus Jakarta Sans (variable, covers all weights)
curl -fsSL -o PlusJakartaSans.ttf       "$base/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf"
curl -fsSL -o PlusJakartaSans-Italic.ttf "$base/plusjakartasans/PlusJakartaSans-Italic%5Bwght%5D.ttf"
# Cormorant Garamond (static weights)
curl -fsSL -o CormorantGaramond-Medium.ttf       "$base/cormorantgaramond/CormorantGaramond-Medium.ttf"
curl -fsSL -o CormorantGaramond-SemiBold.ttf     "$base/cormorantgaramond/CormorantGaramond-SemiBold.ttf"
curl -fsSL -o CormorantGaramond-Bold.ttf         "$base/cormorantgaramond/CormorantGaramond-Bold.ttf"
curl -fsSL -o CormorantGaramond-MediumItalic.ttf "$base/cormorantgaramond/CormorantGaramond-MediumItalic.ttf"
curl -fsSL -o CormorantGaramond-SemiBoldItalic.ttf "$base/cormorantgaramond/CormorantGaramond-SemiBoldItalic.ttf"
# Space Mono (static)
curl -fsSL -o SpaceMono-Regular.ttf "$base/spacemono/SpaceMono-Regular.ttf"
curl -fsSL -o SpaceMono-Bold.ttf    "$base/spacemono/SpaceMono-Bold.ttf"
cd ../../..
file ios/Resources/Fonts/*.ttf
```

Expected: each line reports `TrueType Font data` (or `OpenType`). If any download is HTML/empty (URL moved), find the correct path under `https://github.com/google/fonts/tree/main/ofl/<family>` and re-download before proceeding. Do not commit zero-byte files.

- [ ] **Step 2: Record the exact PostScript names** (needed for `Font.custom`). Run:

```bash
for f in ios/Resources/Fonts/*.ttf; do
  echo "$f -> $(python3 -c "import sys;from fontTools.ttLib import TTFont;print(TTFont(sys.argv[1])['name'].getDebugName(6))" "$f" 2>/dev/null || echo '(install fonttools or read in Font Book)')"
done
```

If `fontTools` is unavailable, open each TTF in Font Book and read the PostScript name. Typical names: `PlusJakartaSans-Regular`/`-Medium`/`-SemiBold`/`-Bold` (variable family exposes these), `CormorantGaramond-Medium`/`-SemiBold`/`-Bold`/`-MediumItalic`/`-SemiBoldItalic`, `SpaceMono-Regular`/`-Bold`. Note the real names in your report; `SynFont` (Task 3) uses them verbatim.

- [ ] **Step 3: Register the fonts in `ios/Sources/Info.plist`** by adding a `UIAppFonts` array of the filenames (inside the top-level `<dict>`):

```xml
  <key>UIAppFonts</key>
  <array>
    <string>PlusJakartaSans.ttf</string>
    <string>PlusJakartaSans-Italic.ttf</string>
    <string>CormorantGaramond-Medium.ttf</string>
    <string>CormorantGaramond-SemiBold.ttf</string>
    <string>CormorantGaramond-Bold.ttf</string>
    <string>CormorantGaramond-MediumItalic.ttf</string>
    <string>CormorantGaramond-SemiBoldItalic.ttf</string>
    <string>SpaceMono-Regular.ttf</string>
    <string>SpaceMono-Bold.ttf</string>
  </array>
```

- [ ] **Step 4: Add the fonts folder to the app target's sources in `ios/project.yml`.** Under the `synzoia` target's `sources:` list (which currently has `- path: Sources`), add:

```yaml
      - path: Resources/Fonts
```

XcodeGen treats unknown file types as resources and copies them into the bundle. (If the build does not copy them, set them explicitly as a `resources:` entry instead.)

- [ ] **Step 5: Regenerate and build.**

```bash
cd ios && xcodegen generate && cd ..
xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia -destination 'platform=iOS Simulator,name=iPhone 17' build
```

Expected: `** BUILD SUCCEEDED **`, and the `.app` bundle contains the fonts: `find ~/Library/Developer/Xcode/DerivedData/synzoia-*/Build/Products/Debug-iphonesimulator/synzoia.app -name '*.ttf' | wc -l` returns 9.

- [ ] **Step 6: Commit.**

```bash
git add ios/Resources/Fonts ios/Sources/Info.plist ios/project.yml
git commit -m "feat(ios): bundle Plus Jakarta Sans, Cormorant Garamond, Space Mono fonts"
```

---

### Task 2: Color palette (SynColor)

Deliverable: a `SynColor` namespace exposing every design token as an exact sRGB `Color`, build-verified.

**Files:** Create `ios/Sources/DesignSystem/SynColor.swift`.

**Interfaces produced:** `enum SynColor` with static `Color` members: `bg, fg, card, card2, muted, primary, primaryFg, border, accent, fern, amber, bark, remPurple`, and an `avatarStops: [Color]` plus named stops `teal, deepTeal, deepFern, amber2, bark2, sky`, and `healthRed`. Plus `static func hex(_ s: String) -> Color`.

- [ ] **Step 1: Write `ios/Sources/DesignSystem/SynColor.swift`.**

```swift
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
```

- [ ] **Step 2: Regenerate, build.** `cd ios && xcodegen generate && cd .. && xcodebuild -project ios/synzoia.xcodeproj -scheme synzoia -destination 'platform=iOS Simulator,name=iPhone 17' build` -> `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Commit.**

```bash
git add ios/Sources/DesignSystem/SynColor.swift
git commit -m "feat(ios): coastal color palette"
```

---

### Task 3: Typography and wordmark

Deliverable: `SynFont` helpers using the bundled fonts, and the `SynWordmark` view, build-verified.

**Files:** Create `ios/Sources/DesignSystem/SynFont.swift`, `ios/Sources/DesignSystem/SynWordmark.swift`.

**Interfaces produced:**
- `enum SynFont { static func serif(_ size: CGFloat, weight: Font.Weight, italic: Bool) -> Font; static func mono(_ size: CGFloat, bold: Bool) -> Font; static func sans(_ size: CGFloat, weight: Font.Weight) -> Font }`
- `struct SynWordmark: View { init(size: CGFloat) }` rendering `syn` + teal `z` + `oia` in serif italic.
- `extension View { func monoLabel() -> ... }` is optional; keep helpers minimal.

- [ ] **Step 1: Write `ios/Sources/DesignSystem/SynFont.swift`** using the PostScript names recorded in Task 1 (adjust the literal names to match Task 1's report if they differ).

```swift
import SwiftUI

/// Brand type. Cormorant Garamond (serif), Space Mono (mono), Plus Jakarta Sans (sans).
enum SynFont {
    static func serif(_ size: CGFloat, weight: Font.Weight = .semibold, italic: Bool = false) -> Font {
        let name: String
        switch (weight, italic) {
        case (.bold, false): name = "CormorantGaramond-Bold"
        case (.bold, true): name = "CormorantGaramond-SemiBoldItalic"
        case (_, true): name = "CormorantGaramond-MediumItalic"
        case (.medium, false): name = "CormorantGaramond-Medium"
        default: name = "CormorantGaramond-SemiBold"
        }
        return .custom(name, size: size)
    }

    static func mono(_ size: CGFloat, bold: Bool = false) -> Font {
        .custom(bold ? "SpaceMono-Bold" : "SpaceMono-Regular", size: size)
    }

    static func sans(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
        // Plus Jakarta Sans variable family exposes named weights.
        let name: String
        switch weight {
        case .bold, .heavy: name = "PlusJakartaSans-Bold"
        case .semibold: name = "PlusJakartaSans-SemiBold"
        case .medium: name = "PlusJakartaSans-Medium"
        default: name = "PlusJakartaSans-Regular"
        }
        return .custom(name, size: size)
    }
}
```

- [ ] **Step 2: Write `ios/Sources/DesignSystem/SynWordmark.swift`.**

```swift
import SwiftUI

/// The "synzoia" wordmark: serif italic with a teal z.
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
    SynWordmark().padding().background(SynColor.bg)
}
```

- [ ] **Step 3: Regenerate, build** -> `** BUILD SUCCEEDED **`. Then capture a quick visual: build, install, launch on the simulator and screenshot to `/tmp/syn-type.png` is optional here; the wordmark is verified in the Feed screen (Task 6). At minimum, confirm `Font.custom` names resolve by checking no runtime "font not found" fallback (the wordmark must render in serif italic, not system font) when it appears in Task 6.

- [ ] **Step 4: Commit.**

```bash
git add ios/Sources/DesignSystem/SynFont.swift ios/Sources/DesignSystem/SynWordmark.swift
git commit -m "feat(ios): brand typography and synzoia wordmark"
```

---

### Task 4: Core components (avatar + cards) with avatar logic tests

Deliverable: reusable views, with unit tests for the only real logic (initials extraction + deterministic gradient selection from a username).

**Files:** Create `ios/Sources/DesignSystem/GradientAvatar.swift`, `ios/Sources/DesignSystem/SynComponents.swift`, `ios/Tests/GradientAvatarTests.swift`.

**Interfaces produced:**
- `struct GradientAvatar: View { init(username: String, size: CGFloat) }`
- `enum AvatarStyle { static func initials(_ username: String) -> String; static func gradient(_ username: String) -> [Color] }` (the testable logic)
- `struct SynCard<Content: View>: View { init(padding: CGFloat = 15, @ViewBuilder content) }`
- `struct MonoLabel: View { init(_ text: String) }` (uppercase, tracked, muted, mono ~10-11pt)
- `struct Pill: View { init(_ text: String, filled: Bool) }`
- `struct SleepStageBar: View { init(rem: Double, core: Double, deep: Double, awake: Double) }` (the segmented bar from the sleep card)
- `struct WeekBars: View { init(values: [Double], highlightLast: Bool) }` (the 7-day bar chart)

- [ ] **Step 1: Write the failing tests `ios/Tests/GradientAvatarTests.swift`.**

```swift
import XCTest
@testable import synzoia

final class GradientAvatarTests: XCTestCase {
    func testInitialsTakeFirstTwoLettersUppercased() {
        XCTAssertEqual(AvatarStyle.initials("micah"), "MI")
        XCTAssertEqual(AvatarStyle.initials("a"), "A")
        XCTAssertEqual(AvatarStyle.initials("@angela"), "AN")   // strips a leading @
        XCTAssertEqual(AvatarStyle.initials(""), "?")
    }

    func testGradientIsDeterministicAndTwoStops() {
        let g1 = AvatarStyle.gradient("micah")
        let g2 = AvatarStyle.gradient("micah")
        XCTAssertEqual(g1.count, 2)
        XCTAssertEqual(g1, g2)                                  // same username -> same gradient
        // different usernames generally differ; at least the API is stable
        XCTAssertEqual(AvatarStyle.gradient("angela").count, 2)
    }
}
```

- [ ] **Step 2: Run, verify failure** (`AvatarStyle` not found).

- [ ] **Step 3: Write `ios/Sources/DesignSystem/GradientAvatar.swift`.**

```swift
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
    HStack { GradientAvatar(username: "micah"); GradientAvatar(username: "angela"); GradientAvatar(username: "peter") }
        .padding().background(SynColor.bg)
}
```

- [ ] **Step 4: Run, verify the two tests pass.**

- [ ] **Step 5: Write `ios/Sources/DesignSystem/SynComponents.swift`** with `SynCard`, `MonoLabel`, `Pill`, `SleepStageBar`, `WeekBars`. Match the design (`sdd/synzoia-app-design.html`): cards use `SynColor.card` bg, 1px `SynColor.border`, radius 16-20; `MonoLabel` is `SynFont.mono(10-11)`, uppercased, `.tracking(1.2)`, `SynColor.muted`; the sleep stage bar is a horizontal `HStack(spacing: 2)` of rounded segments colored REM=`remPurple`, CORE=`primary`, DEEP=`fern`, AWAKE=`muted`, flex-weighted by minutes (design lines 95-96); `WeekBars` is 7 rounded bars, last one full `primary`, others `primary` at ~55% (design lines 228-237).

```swift
import SwiftUI

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

struct MonoLabel: View {
    let text: String
    var size: CGFloat = 11
    var color: Color = SynColor.muted
    init(_ text: String, size: CGFloat = 11, color: Color = SynColor.muted) {
        self.text = text; self.size = size; self.color = color
    }
    var body: some View {
        Text(text.uppercased())
            .font(SynFont.mono(size))
            .tracking(1.4)
            .foregroundStyle(color)
    }
}

struct Pill: View {
    let text: String
    var filled: Bool = false
    init(_ text: String, filled: Bool = false) { self.text = text; self.filled = filled }
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

struct SleepStageBar: View {
    var rem: Double; var core: Double; var deep: Double; var awake: Double
    var body: some View {
        GeometryReader { geo in
            HStack(spacing: 2) {
                seg(rem, SynColor.remPurple); seg(core, SynColor.primary)
                seg(deep, SynColor.fern); seg(awake, SynColor.muted)
            }
        }
        .frame(height: 8)
    }
    private func seg(_ weight: Double, _ color: Color) -> some View {
        Rectangle().fill(color).frame(maxWidth: .infinity).layoutPriority(max(weight, 0.01))
    }
}

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
```

(Note: `SleepStageBar`'s `layoutPriority` weighting is an approximation; if it does not visually distribute, switch to explicit `.frame(width: geo.size.width * fraction)` using a `GeometryReader`. The implementer should screenshot and adjust until it matches design lines 95-96.)

- [ ] **Step 6: Regenerate, run the full suite** -> `** TEST SUCCEEDED **` (33 prior + 2 new = 35). Build must also succeed so the views compile.

- [ ] **Step 7: Commit.**

```bash
git add ios/Sources/DesignSystem/GradientAvatar.swift ios/Sources/DesignSystem/SynComponents.swift ios/Tests/GradientAvatarTests.swift
git commit -m "feat(ios): gradient avatars and coastal UI components"
```

---

### Task 5: Restyle Onboarding to the Join design

Deliverable: the onboarding screen matches the design's Join screen (design lines 366-392), verified by build + screenshot.

**Files:** Modify `ios/Sources/Features/Onboarding/OnboardingView.swift`. (Do NOT change `OnboardingViewModel`; only the view.)

- [ ] **Step 1: Rewrite `OnboardingView`'s body** to the coastal Join layout: full-bleed `SynColor.bg`; a serif italic headline "Join the movement on syn[z]oia" (use the wordmark idea: teal z); a muted body paragraph; a `MonoLabel("Your handle")`; the username field styled as a card with a 1px `SynColor.primary` border, a serif italic "@" prefix in `SynColor.muted`, and the typed handle; a full-width primary button "Claim @<handle>" (`SynColor.primary` bg, `SynColor.primaryFg` text, radius 14); and the 3 numbered steps (accent circles + muted text) adapted to native sync wording: (1) "Claim your handle." (2) "We store your token securely on this phone." (3) "Walk and sleep. You're on the board." Keep the existing `model.username` binding, `model.canSubmit`, `model.state`, `model.join()` and the error display. Open `sdd/synzoia-app-design.html` lines 366-392 for exact sizes/spacing.

(Full code: the implementer writes it from the design; preserve the view-model interface from Phase 1. Keep `#Preview { OnboardingView(api: APIClient(config: .production), onSignIn: { _ in }) }`.)

- [ ] **Step 2: Regenerate, build** -> `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Screenshot.** Boot iPhone 17, install, launch (fresh sim shows onboarding), screenshot to `/tmp/syn-onboarding.png`. Compare to the design Join screen: serif italic headline with teal z, primary-bordered handle field, primary Claim button, 3 numbered steps. Adjust until it matches.

- [ ] **Step 4: Commit.**

```bash
git add ios/Sources/Features/Onboarding/OnboardingView.swift
git commit -m "feat(ios): restyle onboarding to coastal Join design"
```

---

### Task 6: Restyle the Feed to the design

Deliverable: the Feed matches the design (header + title + cards), with each post type rendered in its design card (recap top-3, milestone one-liner, sleep with stage bar, workout, steps text row), NO reaction or comment affordances. Verified by build + screenshot.

**Files:** Modify `ios/Sources/Features/Feed/FeedView.swift` and `ios/Sources/Features/Feed/PostRow.swift` (PostRow becomes the per-type card renderer).

- [ ] **Step 1: Rewrite the Feed header + chrome in `FeedView`** to match design lines 45-58: full-bleed `SynColor.bg`; top row with the `SynWordmark`, a mono "LIVE" indicator (teal dot + glow), and the user avatar/gear (keep `onOpenSettings` on the avatar or a gear); a large serif "Feed" title (~34pt) and a `MonoLabel("Everyone's moving · today")`. Keep the existing `FeedViewModel` state machine and `.refreshable`. The list uses `SynColor.bg`, no separators, the cards spaced ~14.

- [ ] **Step 2: Rewrite `PostRow` to render each post type as its design card** (design lines 60-114), reading `Post.type` and `Post.details`:
  - `leaderboard_recap` -> the large gradient "Top 3 today" card (fern-tinted), serif italic header with a trophy icon, ranked rows (mono rank number colored amber/muted/bark, `GradientAvatar`, `@username`, mono total). NO fire/clap buttons, NO "comments" link.
  - `steps_milestone` -> the one-liner card: avatar + "`@user` hit a `<threshold>` step milestone" + amber trophy icon.
  - `sleep` -> the medium card: avatar + `@user` + mono time; a big serif duration ("8h 02m" from `details.durationMin`); a `SleepStageBar` (use available per-stage minutes if present, else a sensible split) with REM/CORE/DEEP labels.
  - `steps` -> the text-only row: small avatar + mono "`@user` · N steps today" + relative time.
  - `workout` -> the medium card with a "Run" pill (we do not generate these, but render them if present): serif distance + mono detail. If `details` lacks the fields, show a minimal "logged a workout" line.
  Use `GradientAvatar(username:)`, `SynCard`, `MonoLabel`, `Pill`, `SleepStageBar`. Read `sdd/synzoia-app-design.html` lines 60-114 for exact styling.

- [ ] **Step 3: Regenerate, build, run the full suite** (FeedViewModel tests must still pass; the rendering change does not alter the view-model) -> `** BUILD SUCCEEDED **` + `** TEST SUCCEEDED **`.

- [ ] **Step 4: Screenshot against the live backend.** Boot, install, launch; onboard with a throwaway handle if needed so the Feed loads real posts; screenshot to `/tmp/syn-feed.png`. Compare card-by-card to the design Feed. Adjust spacing/fonts/colors until it matches. (The production feed has real recap/sleep/steps/milestone posts to exercise every card.)

- [ ] **Step 5: Commit.**

```bash
git add ios/Sources/Features/Feed/FeedView.swift ios/Sources/Features/Feed/PostRow.swift
git commit -m "feat(ios): restyle feed cards to coastal design"
```

---

### Task 7: Restyle Settings to the Connect design (native-adapted)

Deliverable: the Settings sheet matches the design's Sync/Connect screen (design lines 337-363), adapted to native sync (no Shortcut), verified by build + screenshot.

**Files:** Modify `ios/Sources/Features/Settings/SettingsView.swift`. (Keep the `SyncEngine`/`AppModel` wiring from Phase 2.)

- [ ] **Step 1: Rewrite `SettingsView`** to the coastal layout: full-bleed `SynColor.bg`; a back/Done affordance and a serif italic "Sync" title; an "Apple Health" card (rounded icon tile in `SynColor.primary` tint with a health heart in `healthRed`, "Apple Health", mono "Steps · Sleep", and an "On"/permission control wired to `sync.requestPermission()`); a primary "Sync now" button wired to `sync.syncNow()` with the `.syncing` spinner and `sync.lastResult`/error display (keep the Phase 2 behavior); and a token card (`accent`-tinted) showing `app.token` in mono with a copy button and the "shown only here" note. Replace the design's Shortcut copy with native wording: "synzoia reads Apple Health on this device and syncs on launch and when you tap Sync now." Keep sign-out. Read `sdd/synzoia-app-design.html` lines 337-363 for styling.

- [ ] **Step 2: Regenerate, build, run the full suite** -> green.

- [ ] **Step 3: Screenshot.** Launch, onboard, open the gear -> Settings, screenshot to `/tmp/syn-settings.png`. Compare to the design Connect screen (adapted). Adjust until it matches.

- [ ] **Step 4: Commit.**

```bash
git add ios/Sources/Features/Settings/SettingsView.swift
git commit -m "feat(ios): restyle settings to coastal sync design"
```

---

### Task 8: Phase 3A verification

Deliverable: a clean full suite and a screenshot set proving the coastal look on the three existing screens.

- [ ] **Step 1: Full suite** -> `** TEST SUCCEEDED **` (35 tests).
- [ ] **Step 2: Confirm fonts render (not system fallback).** In the launched app, the wordmark and titles must be Cormorant Garamond (serif), labels Space Mono. If anything renders as the system font, the `Font.custom` PostScript name is wrong (fix `SynFont` to the names from Task 1 Step 2) before declaring done.
- [ ] **Step 3: Capture the screenshot set** (`/tmp/syn-onboarding.png`, `/tmp/syn-feed.png`, `/tmp/syn-settings.png`) and confirm each matches its design screen.
- [ ] **Step 4: No commit (verification only).** Report the screenshot paths.

## Self-Review

**Spec coverage:** Fonts (T1), palette (T2), typography + wordmark (T3), components (T4), and the three existing screens restyled to the design (Onboarding T5 -> Join, Feed T6 -> feed cards, Settings T7 -> Connect). The 4-tab shell, Ranks, Profile, and Groups-coming-soon are explicitly Phase 3B. Reactions/comments omitted per the approved scope. Dark-only per the approved scope.

**Placeholder scan:** Tasks 5/6/7 intentionally delegate exact pixel values to the design source (`sdd/synzoia-app-design.html`, with line ranges) rather than transcribing all 500 lines of HTML; this is a faithful-implementation instruction, not a TBD. All foundation code (palette, fonts, components) is complete. Verification is build + test + screenshot-vs-design.

**Type consistency:** `SynColor.*`, `SynFont.serif/mono/sans`, `SynWordmark`, `AvatarStyle.initials/gradient`, `GradientAvatar(username:size:)`, `SynCard`, `MonoLabel`, `Pill`, `SleepStageBar`, `WeekBars` are defined in Tasks 2-4 and consumed in Tasks 5-7. `WeekBars` is built here but first used in 3B's Profile; that is fine (it is a foundation component).
