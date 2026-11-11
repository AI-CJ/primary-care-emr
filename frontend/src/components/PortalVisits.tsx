import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { PortalVisitSummary } from '../types'

type PortalVisitsProps = {
  patientId: number
}

function PortalVisits({ patientId }: PortalVisitsProps) {
  const [visits, setVisits] = useState<PortalVisitSummary[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadVisits() {
      setIsLoading(true)
      setError(null)
      setVisits(null)

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/portal-preview/visits',
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PortalVisitSummary[] = await response.json()
        if (!controller.signal.aborted) setVisits(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Visits could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Visits could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadVisits()
    return () => controller.abort()
  }, [patientId, refreshCount])

  const recentVisits = visits ?? []

  return (
    <section className="portal-card" aria-labelledby="portal-visits">
      <h2 id="portal-visits">My past visits</h2>
      <p className="portal-help">
        Recent visits with finalized notes in this fictional chart.
        Only instructions written for patients are shown. Draft notes and private clinical details stay in the staff chart.
      </p>

      {isLoading && <p role="status">Loading visits...</p>}
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
      {!isLoading && !error && recentVisits.length === 0 && (
        <p>No finalized visits are available in this preview.</p>
      )}
      {!isLoading && !error && recentVisits.length > 0 && (
        <ul className="portal-records">
          {recentVisits.map((visit) => (
            <li key={visit.id}>
              <strong>{visit.reason_for_visit}</strong>
              <span>
                Visit on <time dateTime={visit.visit_date}>{visit.visit_date}</time>
              </span>
              {visit.patient_instructions && (
                <span className="portal-patient-instructions">
                  <strong>Instructions:</strong> {visit.patient_instructions}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default PortalVisits
