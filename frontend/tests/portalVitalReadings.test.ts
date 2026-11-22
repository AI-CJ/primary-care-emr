import assert from 'node:assert/strict'
import { test } from 'node:test'
import { formatPortalVitalReadings } from '../src/portalVitalReadings.ts'
import type { PortalVitalSummary } from '../src/types.ts'

function vital(values: Partial<PortalVitalSummary> = {}): PortalVitalSummary {
  return {
    id: 1,
    recorded_on: '2026-01-01',
    systolic_bp: null,
    diastolic_bp: null,
    heart_rate: null,
    respiratory_rate: null,
    temperature_c: null,
    oxygen_saturation: null,
    height_cm: null,
    weight_kg: null,
    ...values,
  }
}

test('formats all recorded measurements with labels and units', () => {
  assert.deepEqual(formatPortalVitalReadings(vital({
    systolic_bp: 120,
    diastolic_bp: 80,
    heart_rate: 72,
    respiratory_rate: 15,
    temperature_c: 36.7,
    oxygen_saturation: 98,
    height_cm: 175,
    weight_kg: 80.5,
  })), [
    'Blood pressure: 120/80 mmHg',
    'Heart rate: 72 bpm',
    'Breathing rate: 15 breaths/min',
    'Temperature: 36.7 °C',
    'Oxygen saturation: 98%',
    'Height: 175 cm',
    'Weight: 80.5 kg',
  ])
})

test('does not present incomplete blood pressure as a complete reading', () => {
  assert.deepEqual(formatPortalVitalReadings(vital({
    systolic_bp: 122,
    heart_rate: 65,
  })), ['Heart rate: 65 bpm'])
})

test('omits missing measurements but preserves recorded zero values', () => {
  assert.deepEqual(formatPortalVitalReadings(vital()), [])
  assert.deepEqual(formatPortalVitalReadings(vital({ temperature_c: 0 })), [
    'Temperature: 0 °C',
  ])
})
