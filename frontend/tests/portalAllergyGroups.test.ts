import assert from 'node:assert/strict'
import { test } from 'node:test'
import { groupPortalAllergies } from '../src/portalAllergyGroups.ts'

type AllergyStatus = 'active' | 'inactive'
const item = (id: number, status: AllergyStatus, onset_date: string | null) =>
  ({ id, status, onset_date })

test('separates active and inactive allergy records without mutating chart history', () => {
  const allergies = [
    item(1, 'inactive', '2024-04-01'),
    item(2, 'active', '2025-04-01'),
    item(3, 'inactive', '2025-02-01'),
    item(4, 'active', null),
  ]
  const before = [...allergies]
  const grouped = groupPortalAllergies(allergies)
  assert.deepEqual(grouped.active.map((record) => record.id), [2, 4])
  assert.deepEqual(grouped.inactive.map((record) => record.id), [3, 1])
  assert.deepEqual(allergies, before)
})

test('orders inactive entries by recorded onset, breaking ties by ID', () => {
  const allergies = [
    item(1, 'inactive', null),
    item(2, 'inactive', '2025-01-01'),
    item(3, 'inactive', '2025-01-01'),
    item(4, 'active', '2026-01-01'),
  ]
  assert.deepEqual(groupPortalAllergies(allergies).inactive.map((record) => record.id), [3, 2, 1])
})

test('handles an empty allergy list', () => {
  assert.deepEqual(groupPortalAllergies([]), { active: [], inactive: [] })
})
