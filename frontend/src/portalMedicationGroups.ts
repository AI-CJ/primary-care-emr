import type { PortalMedicationSummary } from './types'

type MedicationWithDates = Pick<
  PortalMedicationSummary,
  'id' | 'status' | 'start_date' | 'end_date'
>

// Keep the recorded history intact; sort a new array rather than mutating API data.
export function groupPortalMedications<T extends MedicationWithDates>(medications: T[]) {
  const active = medications.filter((medication) => medication.status === 'active')
  const past = medications.filter((medication) => medication.status !== 'active')
    .sort((first, second) =>
      (second.end_date ?? second.start_date ?? '').localeCompare(
        first.end_date ?? first.start_date ?? '',
      ) || second.id - first.id)
  return { active, past }
}
