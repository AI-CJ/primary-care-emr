import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { PortalVitalSummary } from '../types'

type PortalVitalsProps = {
  patientId: number
}

function readings(vital: PortalVitalSummary): string[] {
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

function PortalVitals({ patientId }: PortalVitalsProps) {
  const [vitals, setVitals] = useState<PortalVitalSummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadVitals() {
      setIsLoading(true)
      setError(null)
      setVitals(null)

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/portal-preview/vitals',
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PortalVitalSummary[] = await response.json()
        if (!controller.signal.aborted) setVitals(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Vitals could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Vitals could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadVitals()
    return () => controller.abort()
  }, [patientId, refreshCount])

  const recentVitals = vitals ?? []

  return (
    <section className="portal-card" aria-labelledby="portal-vitals">
      <h2 id="portal-vitals">My recent vitals</h2>
      <p className="portal-help">The last three sets of measurements recorded in your chart.</p>

      {isLoading && <p role="status">Loading vitals...</p>}
      {error && (
        <div>
          <p role="alert">{error}</p>
          <button
            type="button"
            className="secondary-action-button"
            onClick={() => setRefreshCount((count) => count + 1)}
          >
            Try Again
          </button>
        </div>
      )}
      {!isLoading && !error && recentVitals.length === 0 && (
        <p>No vitals have been recorded in your chart.</p>
      )}
      {!isLoading && !error && recentVitals.length > 0 && (
        <ul className="portal-records">
          {recentVitals.map((vital) => (
            <li key={vital.id}>
              <strong><time dateTime={vital.recorded_on}>{vital.recorded_on}</time></strong>
              {readings(vital).map((reading) => <span key={reading}>{reading}</span>)}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default PortalVitals
