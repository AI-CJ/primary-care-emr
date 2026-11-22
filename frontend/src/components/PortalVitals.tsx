import { useEffect, useState } from 'react'
import { apiFetch, API_BASE_URL, getApiErrorMessage } from '../api'
import type { PortalVitalSummary } from '../types'
import { formatPortalVitalReadings } from '../portalVitalReadings'

type PortalVitalsProps = {
  patientId?: number
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
        const url = patientId === undefined
          ? API_BASE_URL + '/portal/vitals'
          : API_BASE_URL + '/patients/' + patientId + '/portal-preview/vitals'
        const response = await apiFetch(url, { signal: controller.signal })
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
              {formatPortalVitalReadings(vital).map((reading) => <span key={reading}>{reading}</span>)}
              {formatPortalVitalReadings(vital).length === 0 && (
                <span>No measurements were recorded for this entry.</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default PortalVitals
