import Foundation

/// Matches the backend IngestSleepRequest body. Field names are the wire
/// names (single words, unaffected by snake_case conversion).
struct SleepPayload: Encodable, Equatable {
    let values: String
    let starts: String
    let ends: String
    let types: String
    let duration: String
    let timestamp: String
}

enum HealthPayloadBuilder {
    /// Wall-clock formatter for starts/ends: "Jun 18, 2026 at 11:30 PM".
    /// en_US_POSIX + the device zone, no seconds. The backend zero-pads
    /// day/hour itself, so non-padded output is accepted.
    private static func wallClock(_ zone: TimeZone) -> DateFormatter {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = zone
        f.dateFormat = "MMM d, yyyy 'at' h:mm a"
        return f
    }

    /// ISO-8601 with an explicit offset (mandatory): "2026-06-19T09:00:00-05:00".
    private static func isoWithOffset(_ date: Date, _ zone: TimeZone) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = zone
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ssXXX"
        return f.string(from: date)
    }

    static func buildSleepPayload(from samples: [SleepSample], capturedAt: Date, zone: TimeZone) -> SleepPayload {
        let sorted = samples.sorted { $0.startDate < $1.startDate }
        let wc = wallClock(zone)
        return SleepPayload(
            values: sorted.map { $0.stage.rawValue }.joined(separator: "\n"),
            starts: sorted.map { wc.string(from: $0.startDate) }.joined(separator: "\n"),
            ends: sorted.map { wc.string(from: $0.endDate) }.joined(separator: "\n"),
            types: sorted.map { _ in "Sleep" }.joined(separator: "\n"),
            // Duration is the backend's sole source of minute totals. Compute it
            // from the real second-precision dates, not the truncated wall clock.
            duration: sorted.map { String(Int($0.endDate.timeIntervalSince($0.startDate))) }.joined(separator: "\n"),
            timestamp: isoWithOffset(capturedAt, zone)
        )
    }

    static func buildSteps(total: Int, capturedAt: Date, zone: TimeZone) -> (timestamp: String, total: Int) {
        (timestamp: isoWithOffset(capturedAt, zone), total: total)
    }
}
