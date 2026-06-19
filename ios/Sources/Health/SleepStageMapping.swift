import Foundation

/// Maps an HKCategoryValueSleepAnalysis raw value to a backend stage, or nil
/// to drop the sample (inBed envelopes overlap the staged segments; unknown
/// values are not in the backend vocabulary and would be silently discarded).
func mapSleepStage(hkRawValue: Int) -> SleepSample.Stage? {
    switch hkRawValue {
    case 0: return nil          // inBed
    case 1: return .core        // asleep (legacy catch-all)
    case 2: return .awake       // awake
    case 3: return .core        // asleepUnspecified
    case 4: return .core        // asleepCore
    case 5: return .deep        // asleepDeep
    case 6: return .rem         // asleepREM
    default: return nil
    }
}
