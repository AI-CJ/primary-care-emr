import type { PortalVitalSummary } from './types'

export function formatPortalVitalReadings(vital: PortalVitalSummary): string[] {
  const items: string[] = []
  if (vital.systolic_bp !== null && vital.diastolic_bp !== null) {
    items.push(`Blood pressure: ${vital.systolic_bp}/${vital.diastolic_bp} mmHg`)
  }
  if (vital.heart_rate !== null) items.push(`Heart rate: ${vital.heart_rate} bpm`)
  if (vital.respiratory_rate !== null) {
    items.push(`Breathing rate: ${vital.respiratory_rate} breaths/min`)
  }
  if (vital.temperature_c !== null) {
    items.push(`Temperature: ${vital.temperature_c} °C`)
  }
  if (vital.oxygen_saturation !== null) {
    items.push(`Oxygen saturation: ${vital.oxygen_saturation}%`)
  }
  if (vital.height_cm !== null) items.push(`Height: ${vital.height_cm} cm`)
  if (vital.weight_kg !== null) items.push(`Weight: ${vital.weight_kg} kg`)
  return items
}

