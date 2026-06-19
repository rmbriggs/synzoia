import Foundation

/// A sleep segment, decoupled from HealthKit so the mapping/build logic is
/// pure and unit-testable without constructing HKSample objects.
struct SleepSample: Equatable {
    /// Backend `values` vocabulary. The rawValue is the exact, case-sensitive
    /// string the server matches against (Core/Deep/REM/Awake).
    enum Stage: String, Equatable {
        case core = "Core"
        case deep = "Deep"
        case rem = "REM"
        case awake = "Awake"
    }

    let startDate: Date
    let endDate: Date
    let stage: Stage
}
