import type { Vital } from './types'

/** Choose the most recent dated record; record ID breaks same-date ties consistently.
 * Do not mix measurements from multiple visits or substitute an older value for missing data.
 */
export function latestRecordedVital(records: readonly Vital[]): Vital | undefined {
  return records.reduce<Vital | undefined>((latest, record) =>
    !latest || record.recorded_on > latest.recorded_on ||
      (record.recorded_on === latest.recorded_on && record.id > latest.id) ? record : latest, undefined)
}
