import XCTest
@testable import synzoia

final class HealthPayloadBuilderTests: XCTestCase {
    // America/Chicago is CDT (-05:00) on 2026-06-18/19.
    private let zone = TimeZone(identifier: "America/Chicago")!

    /// Build a Date at a wall-clock instant in `zone`.
    private func date(_ y: Int, _ mo: Int, _ d: Int, _ h: Int, _ mi: Int, _ s: Int) -> Date {
        var c = DateComponents()
        c.year = y; c.month = mo; c.day = d; c.hour = h; c.minute = mi; c.second = s
        c.timeZone = zone
        return Calendar(identifier: .gregorian).date(from: c)!
    }

    func testBuildsExactWorkedExampleBody() {
        let samples = [
            SleepSample(startDate: date(2026, 6, 18, 23, 30, 0),
                        endDate:   date(2026, 6, 19, 0, 14, 1), stage: .deep),   // 2641s
            SleepSample(startDate: date(2026, 6, 19, 0, 14, 1),
                        endDate:   date(2026, 6, 19, 0, 14, 31), stage: .awake), // 30s
            SleepSample(startDate: date(2026, 6, 19, 0, 14, 31),
                        endDate:   date(2026, 6, 19, 6, 30, 0), stage: .core),   // 22529s
        ]
        let captured = date(2026, 6, 19, 9, 0, 0)
        let p = HealthPayloadBuilder.buildSleepPayload(from: samples, capturedAt: captured, zone: zone)

        XCTAssertEqual(p.values, "Deep\nAwake\nCore")
        XCTAssertEqual(p.types, "Sleep\nSleep\nSleep")
        XCTAssertEqual(p.starts, "Jun 18, 2026 at 11:30 PM\nJun 19, 2026 at 12:14 AM\nJun 19, 2026 at 12:14 AM")
        XCTAssertEqual(p.ends, "Jun 19, 2026 at 12:14 AM\nJun 19, 2026 at 12:14 AM\nJun 19, 2026 at 6:30 AM")
        XCTAssertEqual(p.duration, "2641\n30\n22529")
        XCTAssertEqual(p.timestamp, "2026-06-19T09:00:00-05:00")
    }

    func testSortsSamplesByStartAndHasNoTrailingNewline() {
        let samples = [
            SleepSample(startDate: date(2026, 6, 19, 0, 14, 31), endDate: date(2026, 6, 19, 6, 30, 0), stage: .core),
            SleepSample(startDate: date(2026, 6, 18, 23, 30, 0), endDate: date(2026, 6, 19, 0, 14, 0), stage: .deep),
        ]
        let p = HealthPayloadBuilder.buildSleepPayload(from: samples, capturedAt: date(2026, 6, 19, 9, 0, 0), zone: zone)
        XCTAssertEqual(p.values, "Deep\nCore")           // re-sorted by start
        XCTAssertFalse(p.values.hasSuffix("\n"))
        XCTAssertFalse(p.duration.hasSuffix("\n"))
        // equal element counts across all five arrays
        let counts = [p.values, p.starts, p.ends, p.types, p.duration].map { $0.split(separator: "\n", omittingEmptySubsequences: false).count }
        XCTAssertEqual(Set(counts).count, 1)
    }

    func testBuildStepsWithOffset() {
        let steps = HealthPayloadBuilder.buildSteps(total: 8432, capturedAt: date(2026, 6, 19, 9, 0, 0), zone: zone)
        XCTAssertEqual(steps.timestamp, "2026-06-19T09:00:00-05:00")
        XCTAssertEqual(steps.total, 8432)
    }
}
