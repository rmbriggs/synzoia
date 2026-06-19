import Foundation
import HealthKit

/// Real HealthKit-backed reader. Not unit-tested (requires a device with
/// Health data); verified on device in Task 8. The sample -> SleepSample
/// translation reuses the unit-tested mapSleepStage.
final class HealthKitReader: HealthReading {
    private let store = HKHealthStore()

    private var sleepType: HKCategoryType { HKObjectType.categoryType(forIdentifier: .sleepAnalysis)! }
    private var stepType: HKQuantityType { HKQuantityType(.stepCount) }

    func requestAuthorization() async throws {
        guard HKHealthStore.isHealthDataAvailable() else { return }
        try await store.requestAuthorization(toShare: [], read: [sleepType, stepType])
    }

    func fetchSleepSamples(from start: Date, to end: Date) async throws -> [SleepSample] {
        guard HKHealthStore.isHealthDataAvailable() else { return [] }
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: [])
        let descriptor = HKSampleQueryDescriptor(
            predicates: [.sample(type: sleepType, predicate: predicate)],
            sortDescriptors: [SortDescriptor(\.startDate)]
        )
        let results = try await descriptor.result(for: store)
        return results.compactMap { sample -> SleepSample? in
            guard let cat = sample as? HKCategorySample,
                  let stage = mapSleepStage(hkRawValue: cat.value) else { return nil }
            return SleepSample(startDate: cat.startDate, endDate: cat.endDate, stage: stage)
        }
    }

    func fetchTodayStepTotal() async throws -> Int {
        guard HKHealthStore.isHealthDataAvailable() else { return 0 }
        let startOfDay = Calendar.current.startOfDay(for: Date())
        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: Date(), options: .strictStartDate)
        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(
                quantityType: stepType,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum
            ) { _, stats, error in
                if let error { continuation.resume(throwing: error); return }
                let steps = stats?.sumQuantity()?.doubleValue(for: .count()) ?? 0
                continuation.resume(returning: Int(steps.rounded()))
            }
            store.execute(query)
        }
    }
}
