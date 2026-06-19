import XCTest
@testable import synzoia

final class SleepStageMappingTests: XCTestCase {
    func testMappingTable() {
        XCTAssertNil(mapSleepStage(hkRawValue: 0))               // inBed -> drop
        XCTAssertEqual(mapSleepStage(hkRawValue: 1), .core)      // asleep (legacy)
        XCTAssertEqual(mapSleepStage(hkRawValue: 2), .awake)     // awake
        XCTAssertEqual(mapSleepStage(hkRawValue: 3), .core)      // asleepUnspecified
        XCTAssertEqual(mapSleepStage(hkRawValue: 4), .core)      // asleepCore
        XCTAssertEqual(mapSleepStage(hkRawValue: 5), .deep)      // asleepDeep
        XCTAssertEqual(mapSleepStage(hkRawValue: 6), .rem)       // asleepREM
        XCTAssertNil(mapSleepStage(hkRawValue: 99))              // unknown -> drop
    }

    func testStageRawValuesAreBackendVocabulary() {
        XCTAssertEqual(SleepSample.Stage.core.rawValue, "Core")
        XCTAssertEqual(SleepSample.Stage.deep.rawValue, "Deep")
        XCTAssertEqual(SleepSample.Stage.rem.rawValue, "REM")
        XCTAssertEqual(SleepSample.Stage.awake.rawValue, "Awake")
    }
}
