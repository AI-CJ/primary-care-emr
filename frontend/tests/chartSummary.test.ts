import assert from 'node:assert/strict'
import { test } from 'node:test'
import { latestRecordedVital } from '../src/chartSummary.ts'
import type { Vital } from '../src/types.ts'

function record(id: number, date: string, heartRate: number | null = null): Vital {
  return {
    id, patient_id: 1, recorded_on: date, systolic_bp: null, diastolic_bp: null,
    heart_rate: heartRate, respiratory_rate: null, temperature_c: null,
    oxygen_saturation: null, height_cm: null, weight_kg: null, notes: null,
  }
}

test('empty chart has no latest vital record', () => {
  assert.equal(latestRecordedVital([]), undefined)
})

test('chooses newest recorded date, not response order or highest ID', () => {
  const newest = record(2, '2026-11-20')
  const records = [record(9, '2026-11-19', 75), newest, record(3, '2026-01-01')]
  assert.equal(latestRecordedVital(records), newest)
  assert.equal(records[0].id, 9)
  assert.equal(latestRecordedVital(records)?.heart_rate, null)
})

test('same-day records use ID as a deterministic tie breaker', () => {
  const first = record(1, '2026-11-20')
  const second = record(2, '2026-11-20')
  assert.equal(latestRecordedVital([second, first]), second)
})
