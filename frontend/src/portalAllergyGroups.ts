import type { PortalAllergySummary } from './types'

type AllergyWithStatus = Pick<PortalAllergySummary, 'id' | 'status' | 'onset_date'>

// Keep inactive chart history intact and never sort the original API response.
export function groupPortalAllergies<T extends AllergyWithStatus>(allergies: T[]) {
  const active = allergies.filter((allergy) => allergy.status === 'active')
  const inactive = allergies.filter((allergy) => allergy.status === 'inactive')
    .sort((first, second) =>
      (second.onset_date ?? '').localeCompare(first.onset_date ?? '') ||
      second.id - first.id)
  return { active, inactive }
}
