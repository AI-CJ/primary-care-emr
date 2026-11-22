import assert from 'node:assert/strict'
import { test } from 'node:test'
import { groupPortalMedications } from '../src/portalMedicationGroups.ts'

type MedicationStatus = 'active' | 'completed' | 'discontinued'
const item = (id: number, status: MedicationStatus, start_date: string | null, end_date: string | null) =>
  ({ id, status, start_date, end_date })

test('separates active medications from completed and discontinued history without mutating records', () => {
  const medications = [
    item(1, 'completed', '2024-01-01', '2024-03-01'),
    item(2, 'active', '2026-01-01', null),
    item(3, 'discontinued', '2025-01-01', '2025-07-01'),
  ]
  const original = [...medications]
  const grouped = groupPortalMedications(medications)
  assert.deepEqual(grouped.active.map((record) => record.id), [2])
  assert.deepEqual(grouped.past.map((record) => record.id), [3, 1])
  assert.deepEqual(medications, original)
})

test('sorts history by recorded end date, falling back to start date and ID', () => {
  const medications = [
    item(1, 'completed', '2023-01-01', null),
    item(2, 'discontinued', null, '2025-01-01'),
    item(3, 'completed', '2025-01-01', null),
    item(4, 'active', null, null),
  ]
  assert.deepEqual(groupPortalMedications(medications).past.map((record) => record.id), [3, 2, 1])
})

test('handles an empty medication list', () => {
  assert.deepEqual(groupPortalMedications([]), { active: [], past: [] })
})
