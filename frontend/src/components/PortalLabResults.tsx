import { useEffect, useState } from 'react'
import { API_BASE_URL, getApiErrorMessage } from '../api'
import type { LabResult, PatientLabOrder } from '../types'

type PortalLabResultsProps = {
  patientId: number
}

function PortalLabResults({ patientId }: PortalLabResultsProps) {
  const [orders, setOrders] = useState<PatientLabOrder[] | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadResults() {
      setIsLoading(true)
      setError(null)
      setOrders(null)

      try {
        const response = await fetch(
          API_BASE_URL + '/patients/' + patientId + '/lab-orders',
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(await getApiErrorMessage(response))

        const records: PatientLabOrder[] = await response.json()
        if (!controller.signal.aborted) setOrders(records)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(requestError instanceof TypeError
            ? 'Lab results could not be loaded. Check your connection and try again.'
            : requestError instanceof Error
              ? requestError.message
              : 'Lab results could not be loaded.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadResults()
    return () => controller.abort()
  }, [patientId, refreshCount])

  const recentResults = (orders ?? [])
    .filter((order): order is PatientLabOrder & { result: LabResult } =>
      order.status === 'resulted' && order.result !== null)
    .sort((a, b) =>
      b.result.reported_at.localeCompare(a.result.reported_at) || b.id - a.id)
    .slice(0, 3)

  return (
    <section className="portal-card" aria-labelledby="portal-lab-results">
      <h2 id="portal-lab-results">My lab results</h2>
      <p className="portal-help">
        The three most recently reported results in this fictional chart.
        This preview does not have a patient-release process.
      </p>

      {isLoading && <p role="status">Loading lab results...</p>}
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
      {!isLoading && !error && recentResults.length === 0 && (
        <p>No lab results are recorded in your chart.</p>
      )}
      {!isLoading && !error && recentResults.length > 0 && (
        <ul className="portal-records">
          {recentResults.map((order) => (
            <li key={order.id}>
              <strong>{order.test_name}</strong>
              <span>
                Reported <time dateTime={order.result.reported_at}>
                  {order.result.reported_at.slice(0, 10)}
                </time>
              </span>
              <span>
                Collected <time dateTime={order.result.collected_on}>
                  {order.result.collected_on}
                </time>
              </span>
              <span>Result: {order.result.result_text}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default PortalLabResults
